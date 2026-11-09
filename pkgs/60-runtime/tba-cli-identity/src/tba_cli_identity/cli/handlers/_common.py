from __future__ import annotations

import copy
import hashlib
import json
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from tba_cli_identity.cli.artifacts import (
    deployment_from_options,
    write_effective_claims_manifest,
    write_effective_evidence_manifest,
    write_openapi_contract,
    write_openrpc_contract,
)
from tba_cli_identity.cli.boundary import (
    run_boundary_enforcement_check,
    run_contract_sync_check,
    run_evidence_peer_check,
    run_wrapper_hygiene_check,
)
from tba_cli_identity.cli.claims import run_lint
from tba_cli_identity.cli.feature_surface import run_feature_surface_modularity_check
from tba_cli_identity.cli.governance import run_governance_install_check
from tba_cli_identity.cli.metadata import build_cli_conformance_snapshot, build_cli_contract_manifest
from tba_cli_identity.operator_administration import (
    durable_operator_state_root as _durable_operator_state_root,
)
from tba_cli_identity.cli.project_tree import run_migration_plan_check, run_project_tree_layout_check
from tba_cli_identity.cli.reports import (
    build_adr_index,
    build_evidence_bundle,
    build_release_bundle,
    diff_contracts,
    execute_peer_profiles,
    generate_state_reports,
    run_release_gates,
    run_recertification,
    sign_release_bundle,
    verify_release_bundle_signatures,
    summarize_evidence_status,
    validate_openapi_contract,
    validate_openrpc_contract,
    verify_test_classification,
)
from tba_cli_identity.cli.runtime import (
    launch_runtime_profile,
    probe_application_factory,
    run_runtime_foundation_check,
    runtime_evidence_paths,
    write_runtime_profile_report,
)
from tba_runtime_identity.deployment import PROTOCOL_SLICE_REGISTRY, ROUTE_REGISTRY, SURFACE_SET_REGISTRY
from tba_runtime_identity import build_runtime_hash_matrix, build_runtime_plan, get_runner_adapter, runner_registry_manifest


def _display_path(path: Path, repo_root: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _repo_root(arg: str | None) -> Path:
    if arg:
        return Path(arg).resolve()
    cwd = Path.cwd()
    for parent in (cwd, *cwd.parents, *Path(__file__).resolve().parents):
        if (parent / "pkgs" / "layers.toml").is_file() and (parent / "pyproject.toml").is_file():
            return parent
    return cwd


def _resolved_from_args(args: Any):
    surface_sets = list(getattr(args, "surface_set", None) or [])
    if not surface_sets and all(hasattr(args, name) for name in ("public", "admin", "rpc", "diagnostics")):
        if bool(getattr(args, "public", False)):
            surface_sets.append("public-rest")
        if bool(getattr(args, "admin", False)):
            surface_sets.append("admin-rest")
        if bool(getattr(args, "diagnostics", False)):
            surface_sets.append("diagnostics")
    protocol_slices = list(getattr(args, "slice", None) or [])
    if bool(getattr(args, "enable_mtls", False)) and "mtls" not in protocol_slices:
        protocol_slices.append("mtls")
    return deployment_from_options(
        profile=getattr(args, "profile", None),
        surface_sets=surface_sets,
        protocol_slices=protocol_slices,
        extensions=getattr(args, "extension", None),
        plugin_mode=getattr(args, "plugin_mode", None),
        runtime_style=getattr(args, "runtime_style", None),
        issuer=getattr(args, "issuer", None),
        strict=not getattr(args, "no_strict", False) and bool(getattr(args, "strict", True)),
    )


def _serialize(payload: dict[str, Any], fmt: str) -> str:
    if fmt == "yaml":
        return yaml.safe_dump(payload, sort_keys=False)
    if fmt == "text":
        return "\n".join(f"{key}: {value}" for key, value in payload.items()) + "\n"
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _emit(args: Any, payload: dict[str, Any]) -> int:
    rendered = _serialize(payload, getattr(args, "format", "json"))
    output = getattr(args, "output", None)
    if output:
        out_path = Path(output).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered, encoding="utf-8")
    stream = getattr(args, "output_stream", sys.stdout)
    stream.write(rendered)
    return 0


def _emit_with_code(args: Any, payload: dict[str, Any], rc: int = 0) -> int:
    _emit(args, payload)
    return int(rc)


def _claims_summary(repo_root: Path, deployment: Any) -> dict[str, Any]:
    claims_path = write_effective_claims_manifest(repo_root, deployment, profile_label=deployment.profile)
    evidence_path = write_effective_evidence_manifest(repo_root, deployment, profile_label=deployment.profile)
    return {
        "claims_manifest": str(claims_path.relative_to(repo_root)),
        "evidence_manifest": str(evidence_path.relative_to(repo_root)),
        "active_targets": list(deployment.active_targets),
    }


def _report_dir(args: Any) -> Path | None:
    return Path(args.report_dir).resolve() if getattr(args, "report_dir", None) else None


def _strict(args: Any) -> bool:
    return not getattr(args, "no_strict", False) and bool(getattr(args, "strict", True))




def _runner_options_from_args(args: Any) -> dict[str, Any]:
    adapter = get_runner_adapter(getattr(args, "server", "uvicorn"))
    options: dict[str, Any] = {}
    for meta in adapter.flag_metadata:
        if meta.portable:
            continue
        if hasattr(args, meta.name):
            options[meta.name] = getattr(args, meta.name)
    return options


def _selected_runner_profile(report: dict[str, Any], name: str) -> dict[str, Any]:
    for item in report.get("profiles", []):
        if item.get("name") == name:
            return item
    return {"name": name, "status": "unknown"}

def handle_serve(args: Any) -> int:
    repo_root = _repo_root(getattr(args, "repo_root", None))
    deployment = _resolved_from_args(args)
    runner_options = _runner_options_from_args(args)
    runtime_plan = build_runtime_plan(
        deployment=deployment,
        runner=args.server,
        environment=args.environment,
        host=args.host,
        port=args.port,
        uds=args.uds,
        workers=args.workers,
        log_level=args.log_level,
        access_log=bool(args.access_log),
        lifespan=args.lifespan,
        graceful_timeout=int(args.graceful_timeout),
        pid_file=getattr(args, "pid_file", None),
        proxy_headers=bool(args.proxy_headers),
        require_tls=bool(args.require_tls),
        enable_mtls=bool(args.enable_mtls),
        cookies=bool(args.cookies),
        health=bool(args.health),
        metrics=bool(args.metrics),
        public=bool(args.public),
        admin=bool(args.admin),
        rpc=bool(args.rpc),
        diagnostics=bool(args.diagnostics),
        jwks_refresh_seconds=int(args.jwks_refresh_seconds),
        runner_options=runner_options,
    )
    runtime_profile_report = write_runtime_profile_report(
        repo_root,
        deployment=deployment,
        environment=args.environment,
        host=args.host,
        port=args.port,
        workers=args.workers,
        access_log=bool(args.access_log),
        lifespan=args.lifespan,
        graceful_timeout=int(args.graceful_timeout),
        report_dir=_report_dir(args),
        enable_execution_probes=False,
    )
    selected_profile = _selected_runner_profile(runtime_profile_report, args.server)
    payload = {
        "command": "serve",
        "server": args.server,
        "launch_mode": "check" if bool(getattr(args, "check", False)) else ("dry-run" if bool(getattr(args, "dry_run", False)) else "live"),
        "runtime_plan": runtime_plan.to_manifest(),
        "selected_runner_profile": selected_profile,
        "application_probe": runtime_profile_report.get("application_probe", {}),
        "runtime_profile_summary": runtime_profile_report.get("summary", {}),
        "runner_profile_report_paths": {
            "json": str(((_report_dir(args) or (repo_root / "docs" / "compliance")) / "runtime_profile_report.json").relative_to(repo_root)),
            "md": str(((_report_dir(args) or (repo_root / "docs" / "compliance")) / "runtime_profile_report.md").relative_to(repo_root)),
        },
        "runner_registry": runner_registry_manifest(),
    }
    if bool(getattr(args, "dry_run", False)):
        return _emit(args, payload)

    app_probe, app = probe_application_factory(deployment=deployment)
    payload["application_probe"] = app_probe.to_manifest()
    profile_ready = selected_profile.get("status") == "ready" and app_probe.passed

    if bool(getattr(args, "check", False)) or not profile_ready:
        payload["launch_ready"] = profile_ready
        if not profile_ready:
            payload["launch_blocked_reason"] = "runner profile is not ready for launch in the current environment"
        rc = 0 if profile_ready else 1
        _emit(args, payload)
        return rc

    evidence_paths = runtime_evidence_paths(repo_root, args.server)
    payload["runtime_evidence"] = {
        "startup": str(evidence_paths["startup"].relative_to(repo_root)),
        "shutdown": str(evidence_paths["shutdown"].relative_to(repo_root)),
    }
    _emit(args, payload)
    adapter = get_runner_adapter(args.server)
    return int(
        launch_runtime_profile(
            repo_root,
            app=app,
            plan=runtime_plan,
            adapter=adapter,
            startup_payload=payload,
            evidence_paths=evidence_paths,
        )
    )


def handle_verify(args: Any) -> int:
    repo_root = _repo_root(args.repo_root)
    report_dir = _report_dir(args)
    strict = _strict(args)
    scope = args.scope
    if scope == "governance":
        return run_governance_install_check(repo_root, strict=strict, report_dir=report_dir)
    if scope == "claims":
        return run_lint(repo_root, strict=strict, report_dir=report_dir)
    if scope == "runtime-foundation":
        return run_runtime_foundation_check(repo_root, strict=strict, report_dir=report_dir)
    if scope == "feature-surface-modularity":
        return run_feature_surface_modularity_check(repo_root, strict=strict, report_dir=report_dir)
    if scope == "boundary-enforcement":
        return run_boundary_enforcement_check(repo_root, strict=strict, report_dir=report_dir)
    if scope == "wrapper-hygiene":
        return run_wrapper_hygiene_check(repo_root, strict=strict, report_dir=report_dir)
    if scope == "contract-sync":
        return run_contract_sync_check(repo_root, strict=strict, report_dir=report_dir)
    if scope == "contracts":
        return 0 if validate_openapi_contract(repo_root).passed and validate_openrpc_contract(repo_root).passed else 1
    if scope == "evidence-peer":
        return run_evidence_peer_check(repo_root, strict=strict, report_dir=report_dir)
    if scope == "project-tree-layout":
        return run_project_tree_layout_check(repo_root, strict=strict, report_dir=report_dir)
    if scope == "migration-plan":
        return run_migration_plan_check(repo_root, strict=strict, report_dir=report_dir)
    if scope == "state-reports":
        generate_state_reports(repo_root)
        return 0
    if scope == "test-classification":
        return 0 if verify_test_classification(repo_root, strict=strict)["passed"] else 1
    if scope == "release-gates":
        return 0 if run_release_gates(repo_root, strict=strict)["passed"] else 1
    if scope == "all":
        checks = [
            run_governance_install_check(repo_root, strict=strict, report_dir=report_dir),
            run_lint(repo_root, strict=strict, report_dir=report_dir),
            run_runtime_foundation_check(repo_root, strict=strict, report_dir=report_dir),
            run_feature_surface_modularity_check(repo_root, strict=strict, report_dir=report_dir),
            run_boundary_enforcement_check(repo_root, strict=strict, report_dir=report_dir),
            run_wrapper_hygiene_check(repo_root, strict=strict, report_dir=report_dir),
            run_contract_sync_check(repo_root, strict=strict, report_dir=report_dir),
            run_evidence_peer_check(repo_root, strict=strict, report_dir=report_dir),
            run_project_tree_layout_check(repo_root, strict=strict, report_dir=report_dir),
            run_migration_plan_check(repo_root, strict=strict, report_dir=report_dir),
        ]
        contract_ok = validate_openapi_contract(repo_root).passed and validate_openrpc_contract(repo_root).passed
        classification_ok = verify_test_classification(repo_root, strict=strict)["passed"]
        generate_state_reports(repo_root)
        gate_ok = run_release_gates(repo_root, strict=strict)["passed"]
        return 0 if all(rc == 0 for rc in checks) and contract_ok and classification_ok and gate_ok else 1
    raise ValueError(f"Unsupported verify scope: {scope}")


def handle_gate(args: Any) -> int:
    payload = run_release_gates(_repo_root(args.repo_root), gate_name=args.name, strict=_strict(args))
    payload["command"] = "gate"
    return _emit(args, payload)


def handle_spec_generate(args: Any) -> int:
    repo_root = _repo_root(args.repo_root)
    deployment = _resolved_from_args(args)
    generated: list[str] = []
    if args.kind in {"openapi", "all"}:
        generated.append(str(write_openapi_contract(repo_root, deployment).relative_to(repo_root)))
        for profile in ("baseline", "production", "hardening"):
            generated.append(str(write_openapi_contract(repo_root, deployment_from_options(profile=profile), profile_label=profile).relative_to(repo_root)))
    if args.kind in {"openrpc", "all"}:
        generated.append(str(write_openrpc_contract(repo_root, deployment).relative_to(repo_root)))
        for profile in ("baseline", "production", "hardening"):
            generated.append(str(write_openrpc_contract(repo_root, deployment_from_options(profile=profile), profile_label=profile).relative_to(repo_root)))
    payload = {"command": "spec.generate", "generated": generated}
    payload.update(_claims_summary(repo_root, deployment))
    return _emit(args, payload)


def handle_spec_validate(args: Any) -> int:
    repo_root = _repo_root(args.repo_root)
    reports: list[dict[str, Any]] = []
    if args.kind in {"openapi", "all"}:
        report = validate_openapi_contract(repo_root)
        reports.append({"kind": report.kind, "path": str(report.path.relative_to(repo_root)), "passed": report.passed, "summary": report.summary, "failures": report.failures})
    if args.kind in {"openrpc", "all"}:
        report = validate_openrpc_contract(repo_root)
        reports.append({"kind": report.kind, "path": str(report.path.relative_to(repo_root)), "passed": report.passed, "summary": report.summary, "failures": report.failures})
    return _emit(args, {"command": "spec.validate", "reports": reports})


def handle_spec_diff(args: Any) -> int:
    payload = diff_contracts(_repo_root(args.repo_root), kind=args.kind)
    payload["command"] = "spec.diff"
    return _emit(args, payload)


def handle_spec_report(args: Any) -> int:
    repo_root = _repo_root(args.repo_root)
    openapi = validate_openapi_contract(repo_root)
    openrpc = validate_openrpc_contract(repo_root)
    return _emit(args, {
        "command": "spec.report",
        "openapi": {"passed": openapi.passed, "summary": openapi.summary, "path": str(openapi.path.relative_to(repo_root))},
        "openrpc": {"passed": openrpc.passed, "summary": openrpc.summary, "path": str(openrpc.path.relative_to(repo_root))},
    })


def handle_claims_lint(args: Any) -> int:
    return run_lint(_repo_root(args.repo_root), strict=_strict(args), report_dir=_report_dir(args))


def handle_claims_show(args: Any) -> int:
    repo_root = _repo_root(args.repo_root)
    deployment = _resolved_from_args(args)
    path = write_effective_claims_manifest(repo_root, deployment, profile_label=deployment.profile)
    return _emit(args, {"command": "claims.show", "manifest": str(path.relative_to(repo_root)), "active_targets": list(deployment.active_targets)})


def handle_claims_status(args: Any) -> int:
    repo_root = _repo_root(args.repo_root)
    state = generate_state_reports(repo_root)
    deployment = _resolved_from_args(args)
    payload = {"command": "claims.status", "current_state": state["current_state"], "certification_state": state["certification_state"]}
    payload.update(_claims_summary(repo_root, deployment))
    return _emit(args, payload)


def handle_evidence_bundle(args: Any) -> int:
    repo_root = _repo_root(args.repo_root)
    deployment = _resolved_from_args(args)
    bundle = build_evidence_bundle(repo_root, deployment, tier=args.tier, profile_label=deployment.profile, bundle_dir=Path(args.bundle_dir).resolve() if args.bundle_dir else None)
    return _emit(args, {"command": "evidence.bundle", "bundle_dir": str(bundle.relative_to(repo_root)), "tier": args.tier})


def handle_evidence_status(args: Any) -> int:
    payload = summarize_evidence_status(_repo_root(args.repo_root))
    payload["command"] = "evidence.status"
    return _emit(args, payload)
