from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import signal
import subprocess
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib
from contextlib import suppress
from datetime import datetime, timezone
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any

from tba_cli_identity.cli.certification_evidence import (
    environment_identity_ready,
    install_evidence_ready,
    runtime_surface_probe_ready,
    validated_runtime_manifest_passed,
)
from tba_primitives_identity.path_safety import sanitize_local_paths
from tba_operator_identity.repo_truth import workflow_role_text
from tba_runtime_identity import build_runtime_hash_matrix, build_runtime_plan, get_runner_adapter, iter_runner_adapters
from tba_runtime_identity.types import ApplicationProbeResult, CommandProbeResult, HttpEndpointProbeResult

FORBIDDEN_IMPORT_PATTERNS = [
    re.compile(r"^\s*from\s+fastapi\b", re.MULTILINE),
    re.compile(r"^\s*import\s+fastapi\b", re.MULTILINE),
    re.compile(r"^\s*from\s+starlette\b", re.MULTILINE),
    re.compile(r"^\s*import\s+starlette\b", re.MULTILINE),
]
FORBIDDEN_RUNTIME_IMPORT_PATTERNS = [
    re.compile(r"^\s*from\s+tigrbl_core\b", re.MULTILINE),
    re.compile(r"^\s*import\s+tigrbl_core\b", re.MULTILINE),
    re.compile(r"^\s*from\s+tigrbl\._", re.MULTILINE),
    re.compile(r"^\s*import\s+tigrbl\._", re.MULTILINE),
    re.compile(r"^\s*from\s+tigrbl\.security\.dependencies\b", re.MULTILINE),
    re.compile(
        r"^\s*from\s+tigrbl\.types\s+import\s+.*\b(HTTPException|Request|Response|Depends|Security)\b",
        re.MULTILINE,
    ),
]
FORBIDDEN_FALLBACK_PATTERNS = [
    re.compile(r"pragma:\s*no\s*cover\s*-\s*import-safety fallback"),
    re.compile(r"^\s*if\s+hasattr\(", re.MULTILINE),
    re.compile(r"^\s*except\s+Exception:\s*$", re.MULTILINE),
]
FORBIDDEN_DEPENDENCY_NAMES = {"fastapi", "starlette"}
SUPPORTED_CERTIFICATION_PYTHON_VERSIONS = ["3.10", "3.11", "3.12"]
TIGRCORN_CERTIFICATION_PYTHON_VERSIONS = ["3.11", "3.12"]
RUNNER_CERTIFICATION_MATRIX = {
    "uvicorn": {
        "profile_name": "sqlite-uvicorn",
        "supported_python_versions": SUPPORTED_CERTIFICATION_PYTHON_VERSIONS,
        "ci_install_job": "sqlite-uvicorn",
        "required_extra": "uvicorn",
        "required_release_probe": "--runner uvicorn",
    },
    "hypercorn": {
        "profile_name": "postgres-hypercorn",
        "supported_python_versions": SUPPORTED_CERTIFICATION_PYTHON_VERSIONS,
        "ci_install_job": "postgres-hypercorn",
        "required_extra": "hypercorn",
        "required_release_probe": "--runner hypercorn",
    },
    "tigrcorn": {
        "profile_name": "tigrcorn",
        "supported_python_versions": TIGRCORN_CERTIFICATION_PYTHON_VERSIONS,
        "ci_install_job": "tigrcorn",
        "required_extra": "tigrcorn",
        "required_release_probe": "--runner tigrcorn",
    },
}

RUNTIME_VALIDATION_GROUPS = {
    "base": {"supported_python_versions": SUPPORTED_CERTIFICATION_PYTHON_VERSIONS},
    "sqlite-uvicorn": {"supported_python_versions": SUPPORTED_CERTIFICATION_PYTHON_VERSIONS},
    "postgres-hypercorn": {"supported_python_versions": SUPPORTED_CERTIFICATION_PYTHON_VERSIONS},
    "tigrcorn": {"supported_python_versions": TIGRCORN_CERTIFICATION_PYTHON_VERSIONS},
    "devtest": {"supported_python_versions": SUPPORTED_CERTIFICATION_PYTHON_VERSIONS},
}


_RUNTIME_HTTP_SURFACE_TARGETS = (
    {"name": "openid-configuration", "path": "/.well-known/openid-configuration"},
    {"name": "oauth-authorization-server", "path": "/.well-known/oauth-authorization-server"},
    {"name": "oauth-protected-resource", "path": "/.well-known/oauth-protected-resource"},
    {"name": "jwks", "path": "/.well-known/jwks.json"},
    {"name": "public-contract", "path": "/openapi.json"},
)


def _deployment_from_app_state(app: Any) -> Any | None:
    state = getattr(app, "state", None)
    if state is None:
        return None
    return getattr(state, "tba_auth_deployment", None)


def _surface_probe_targets(*, app: Any, deployment: Any | None = None) -> tuple[dict[str, str], ...]:
    active_deployment = deployment or _deployment_from_app_state(app)
    if active_deployment is None or not hasattr(active_deployment, "active_routes"):
        return _RUNTIME_HTTP_SURFACE_TARGETS

    active_routes = set(getattr(active_deployment, "active_routes", ()) or ())
    surface_enabled = getattr(active_deployment, "surface_enabled", None)
    public_surface_enabled = bool(surface_enabled("public-rest")) if callable(surface_enabled) else True

    filtered_targets: list[dict[str, str]] = []
    for item in _RUNTIME_HTTP_SURFACE_TARGETS:
        path = str(item["path"])
        if path == "/openapi.json":
            if public_surface_enabled:
                filtered_targets.append(item)
            continue
        if path in active_routes:
            filtered_targets.append(item)
    return tuple(filtered_targets) or _RUNTIME_HTTP_SURFACE_TARGETS


RUNTIME_FALLBACK_PATHS = [
    "tba_auth/framework.py",
    "tba_auth/plugin.py",
    "pkgs/90-backend-apps/tba-app-backend-core/src/tba_app_backend_core/app.py",
    "pkgs/60-runtime/tba-server-identity/src/tba_server_identity/composition/lifecycle.py",
    "tba_auth/app.py",
    "tba_auth/gateway.py",
]


def _scan_patterns(
    base: Path,
    patterns: list[re.Pattern[str]],
    *,
    rel_root: Path,
) -> list[dict[str, str | int]]:
    hits: list[dict[str, str | int]] = []
    if not base.exists():
        return hits
    paths = [base] if base.is_file() else list(base.rglob("*.py"))
    for path in paths:
        if path.is_dir():
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in patterns:
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                hits.append(
                    {
                        "path": str(path.relative_to(rel_root)),
                        "line": line,
                        "match": match.group(0).strip(),
                    }
                )
    return hits



def _load_pyproject_runtime_manifest(repo_root: Path) -> dict[str, Any]:
    pyproject_path = repo_root / "pkgs" / "60-runtime" / "tba-runtime-identity" / "pyproject.toml"
    if not pyproject_path.exists():
        return {}
    return tomllib.loads(pyproject_path.read_text(encoding="utf-8"))



def _build_runner_support_manifest(repo_root: Path) -> dict[str, Any]:
    pyproject = _load_pyproject_runtime_manifest(repo_root)
    project = pyproject.get("project", {}) if isinstance(pyproject, dict) else {}
    optional_dependencies = project.get("optional-dependencies", {}) or {}
    requires_python = str(project.get("requires-python", "unspecified"))
    tox_text = (repo_root / "tox.ini").read_text(encoding="utf-8") if (repo_root / "tox.ini").exists() else ""
    install_workflow_text = workflow_role_text(repo_root, "install-matrix")
    release_workflow_text = workflow_role_text(repo_root, "release-gates")

    profiles: dict[str, Any] = {}
    for runner, config in RUNNER_CERTIFICATION_MATRIX.items():
        supported_python_versions = list(config["supported_python_versions"])
        expected_tox_envs = [f"py{version.replace('.', '')}-{config['profile_name']}" for version in supported_python_versions]
        extra_values = list(optional_dependencies.get(config["required_extra"], []) or [])
        servers_extra_values = list(optional_dependencies.get("servers", []) or [])
        tox_envs_present = [env for env in expected_tox_envs if env in tox_text]
        release_probe_present = config["required_release_probe"] in tox_text or config["required_release_probe"] in release_workflow_text
        ci_install_job_present = config["ci_install_job"] in install_workflow_text
        placeholder_supported = len(extra_values) == 0
        aggregate_runner_extra_present = any(runner in value for value in servers_extra_values)
        profiles[runner] = {
            "required_extra": config["required_extra"],
            "profile_name": config["profile_name"],
            "supported_python_versions": supported_python_versions,
            "pyproject_extra_present": not placeholder_supported,
            "pyproject_extra_values": extra_values,
            "aggregate_runner_extra_present": aggregate_runner_extra_present,
            "tox_envs": expected_tox_envs,
            "tox_envs_present": tox_envs_present,
            "ci_install_job": config["ci_install_job"],
            "ci_install_job_present": ci_install_job_present,
            "ci_release_gate_probe_present": release_probe_present,
            "placeholder_supported": placeholder_supported,
            "declared_installable_from_repository": (not placeholder_supported)
            and len(tox_envs_present) == len(expected_tox_envs)
            and ci_install_job_present
            and release_probe_present,
        }
    return {
        "requires_python": requires_python,
        "supported_python_versions": SUPPORTED_CERTIFICATION_PYTHON_VERSIONS,
        "profiles": profiles,
    }


def _scan_pyproject_forbidden_dependencies(pyproject_path: Path) -> list[str]:
    if not pyproject_path.exists():
        return []
    text = pyproject_path.read_text(encoding="utf-8").lower()
    hits: list[str] = []
    for dep in sorted(FORBIDDEN_DEPENDENCY_NAMES):
        if f'"{dep}' in text or f"'{dep}" in text:
            hits.append(dep)
    return hits



def _read_json_if_exists(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}



def _coerce_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None



def _runtime_manifest_counts_as_passed(payload: dict[str, Any]) -> bool:
    return validated_runtime_manifest_passed(payload)



def _runtime_manifest_failure_reasons(payload: dict[str, Any]) -> list[str]:
    if not payload:
        return ["manifest is missing"]
    reasons: list[str] = []
    if not environment_identity_ready(payload):
        reasons.append("environment identity is missing or does not match the manifest python version")
    if not install_evidence_ready(payload):
        reasons.append("install substrate evidence is missing or incomplete")
    if not payload.get("runtime_smoke_passed", False):
        reasons.append("runtime smoke did not pass")
    if not payload.get("application_probe_passed", False):
        reasons.append("application-factory probe did not pass")
    if not runtime_surface_probe_ready(payload):
        reasons.append("HTTP surface probe evidence is missing or failed")
    runner = str(payload.get("runner") or "").strip()
    if runner and not payload.get("runner_available", False):
        reasons.append(f"runner package '{runner}' was not available in the validated environment")
    if runner and not payload.get("serve_check_passed", False):
        reasons.append("serve-check evidence is missing or failed")
    if not payload.get("passed", False):
        reasons.append("manifest pass bit is false")
    return reasons or ["manifest did not satisfy the certification runtime criteria"]



def _validated_artifact_inventory_present(repo_root: Path) -> bool:
    validated_root = repo_root / "dist" / "validated-runs"
    if not validated_root.exists():
        return False
    if (validated_root / "collected-artifact-downloads.json").exists():
        return True
    recognized_kinds = {"runtime-profile", "test-lane", "migration-portability", "tier3-evidence"}
    for path in sorted(validated_root.glob("*.json")):
        payload = _read_json_if_exists(path)
        if str(payload.get("kind", "")) in recognized_kinds:
            return True
    return False



def _runtime_report_mode(repo_root: Path, report_mode: str | None) -> str:
    requested = (report_mode or os.environ.get("TBA_AUTH_RUNTIME_REPORT_MODE", "auto")).strip().lower() or "auto"
    if requested in {"validated-runs", "live-probe"}:
        return requested
    return "validated-runs" if _validated_artifact_inventory_present(repo_root) else "live-probe"



def _validated_runtime_manifest_map(repo_root: Path) -> dict[tuple[str, str], dict[str, Any]]:
    manifests: dict[tuple[str, str], dict[str, Any]] = {}
    validated_root = repo_root / "dist" / "validated-runs"
    if not validated_root.exists():
        return manifests
    for path in sorted(validated_root.glob("*.json")):
        payload = _read_json_if_exists(path)
        if payload.get("kind") != "runtime-profile":
            continue
        profile = str(payload.get("matrix_profile", "unknown"))
        python_version = str(payload.get("python_version", ""))
        if not profile or not python_version:
            continue
        payload["_path"] = str(path.relative_to(repo_root))
        manifests[(profile, python_version)] = payload
    return manifests



def _matrix_identities(profile: str, versions: list[str]) -> list[str]:
    return [f"{profile}@py{version}" for version in versions]



def _runtime_summary_from_manifests(manifests: list[dict[str, Any]]) -> dict[str, int]:
    endpoint_count = 0
    passed_count = 0
    failed_count = 0
    for manifest in manifests:
        endpoint_count = max(
            endpoint_count,
            _coerce_int(manifest.get("surface_probe_endpoint_count"))
            or _coerce_int((manifest.get("surface_probe") or {}).get("endpoint_count"))
            or 0,
        )
        passed_count = max(
            passed_count,
            _coerce_int(manifest.get("surface_probe_passed_count"))
            or _coerce_int((manifest.get("surface_probe") or {}).get("passed_count"))
            or 0,
        )
        failed_count = max(
            failed_count,
            _coerce_int(manifest.get("surface_probe_failed_count"))
            or _coerce_int((manifest.get("surface_probe") or {}).get("failed_count"))
            or 0,
        )
    return {
        "endpoint_count": endpoint_count,
        "passed_count": passed_count,
        "failed_count": failed_count,
    }
