from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tba_operator_identity.repo_truth import (
    has_install_matrix_workflow,
    has_release_gate_workflow,
    workflow_paths,
    workflow_role_paths,
)

DOCS_DIR = REPO_ROOT / "docs" / "compliance"
MD_OUT = DOCS_DIR / "PACKAGE_REVIEW_GAP_ANALYSIS.md"
JSON_OUT = DOCS_DIR / "PACKAGE_REVIEW_GAP_ANALYSIS.json"

WORKSPACE_IMPORTS = (
    "tigrbl",
    "swarmauri_core",
    "swarmauri_base",
    "swarmauri_standard",
    "swarmauri_tokens_jwt",
    "swarmauri_signing_jws",
    "swarmauri_signing_ed25519",
    "swarmauri_signing_dpop",
    "pqcrypto",
    "swarmauri_crypto_jwe",
    "swarmauri_crypto_paramiko",
    "swarmauri_keyprovider_file",
    "swarmauri_keyprovider_local",
)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def find_local_dependency_gaps() -> list[str]:
    missing: list[str] = []
    for name in WORKSPACE_IMPORTS:
        if importlib.util.find_spec(name) is None:
            missing.append(name)
    return missing


def build_review() -> dict[str, Any]:
    current = load_json(REPO_ROOT / "docs" / "compliance" / "current_state_report.json")
    cert = load_json(REPO_ROOT / "docs" / "compliance" / "certification_state_report.json")
    gates = load_json(REPO_ROOT / "docs" / "compliance" / "release_gate_report.json")
    matrix = load_json(REPO_ROOT / "docs" / "compliance" / "final_target_decision_matrix.json")
    authority = load_json(REPO_ROOT / "docs" / "compliance" / "AUTHORITATIVE_CURRENT_DOCS.json")
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    rows = matrix.get("rows", [])
    complete_rows = [row for row in rows if row.get("status") in {"certifiably-complete", "complete-but-not-independently-peer-certified"}]
    partial_rows = [row for row in rows if row.get("status") not in {"certifiably-complete", "complete-but-not-independently-peer-certified"}]

    return {
        "schema_version": 1,
        "package": matrix.get("package", "tba_auth"),
        "delivery_lifecycle": matrix.get("delivery_lifecycle", matrix.get("delivery_track", "unknown")),
        "version": pyproject.get("project", {}).get("version", "0.0.0"),
        "summary": {
            "fully_certifiable_now": bool(cert.get("summary", {}).get("fully_certifiable_now", False)),
            "fully_rfc_compliant_now": bool(cert.get("summary", {}).get("fully_rfc_compliant_now", False)),
            "release_gates_passed": bool(gates.get("passed", False)),
            "complete_target_count": len(complete_rows),
            "partial_target_count": len(partial_rows),
        },
        "document_authority": {
            "path": "docs/compliance/AUTHORITATIVE_CURRENT_DOCS.md",
            "authoritative_current_docs": authority.get("authoritative_current_docs", []),
            "derived_current_docs": authority.get("derived_current_docs", []),
            "archived_historical_roots": [authority.get("archive_root", "docs/archive/")],
            "current_release_bundle_docs": authority.get("certification_bundle_generated_current_docs", []),
        },
        "clean_room_matrix": {
            "implemented": bool(current.get("summary", {}).get("clean_room_matrix_implemented", False)),
            "tox_manifest": "tox.ini",
            "install_workflow": next(iter(workflow_role_paths(REPO_ROOT, "install-matrix")), None) if has_install_matrix_workflow(REPO_ROOT) else None,
            "release_gate_workflow": next(iter(workflow_role_paths(REPO_ROOT, "release-gates")), None) if has_release_gate_workflow(REPO_ROOT) else None,
            "recognized_workflows": workflow_paths(REPO_ROOT),
            "tigrcorn_pin_committed": bool(current.get("summary", {}).get("tigrcorn_pin_committed", False)),
            "executed_in_this_container": bool(current.get("summary", {}).get("clean_room_matrix_executed_in_this_container", False)),
        },
        "complete_targets": [
            {
                "target": row.get("target"),
                "claim_tier": row.get("claim_tier"),
                "profile": row.get("profile"),
            }
            for row in complete_rows
        ],
        "partial_targets": [
            {
                "target": row.get("target"),
                "claim_tier": row.get("claim_tier"),
                "profile": row.get("profile"),
                "status": row.get("status"),
                "claim_status": row.get("claim_status"),
            }
            for row in partial_rows
        ],
        "certification_gaps": [str(item) for item in cert.get("summary", {}).get("open_gaps", [])],
        "development_and_packaging_gaps": {
            "workspace_dependency_imports_missing_locally": find_local_dependency_gaps(),
            "pytest_local_bootstrap": "Runtime and test generation still depend on external packages that may be missing in isolated containers.",
        },
        "required_changes_for_full_certification": [
            "Preserve validated clean-room runtime matrix results across Python 3.10, 3.11, 3.12, 3.13, and 3.14.",
            "Preserve validated in-scope certification lane execution results and carry them into the validated execution manifest.",
            "Preserve SQLite and PostgreSQL migration portability validation for upgrade → downgrade → reapply.",
            "Rebuild Tier 3 evidence from validated runs before claiming the final certification release.",
            "Keep historical/non-authoritative docs archived or visibly marked, and keep certification bundles limited to generated current-state docs.",
        ],
    }


def render_markdown(review: dict[str, Any]) -> str:
    lines: list[str] = []
    append = lines.append
    append("# Package review gap analysis")
    append("")
    append(f"- package: `{review['package']}`")
    append(f"- version: `{review['version']}`")
    append(f"- delivery lifecycle: `{review['delivery_lifecycle']}`")
    append(f"- fully certifiable now: `{review['summary']['fully_certifiable_now']}`")
    append(f"- fully RFC compliant now: `{review['summary']['fully_rfc_compliant_now']}`")
    append(f"- release gates passed: `{review['summary']['release_gates_passed']}`")
    append(f"- complete targets: `{review['summary']['complete_target_count']}`")
    append(f"- partial targets: `{review['summary']['partial_target_count']}`")
    append("")
    append("## Documentation authority")
    append("")
    append(f"- authority manifest: `{review['document_authority']['path']}`")
    append(f"- authoritative current docs: `{len(review['document_authority']['authoritative_current_docs'])}`")
    append(f"- archived historical roots: `{review['document_authority']['archived_historical_roots']}`")
    append(f"- certification bundle current-state docs: `{review['document_authority']['current_release_bundle_docs']}`")
    append("")
    append("## Clean-room certification matrix checkpoint")
    append("")
    append(f"- implemented: `{review['clean_room_matrix']['implemented']}`")
    append(f"- local/CI runner manifest: `{review['clean_room_matrix']['tox_manifest']}`")
    append(f"- install workflow: `{review['clean_room_matrix']['install_workflow']}`")
    append(f"- release-gate workflow: `{review['clean_room_matrix']['release_gate_workflow']}`")
    append(f"- tigrcorn pin committed: `{review['clean_room_matrix']['tigrcorn_pin_committed']}`")
    append(f"- full matrix execution preserved in this container: `{review['clean_room_matrix']['executed_in_this_container']}`")
    append("")
    append("## Certification blockers")
    append("")
    for item in review["certification_gaps"]:
        append(f"- {item}")
    append("")
    append("## Development and packaging gaps")
    append("")
    append(f"- locally missing workspace/runtime dependencies: `{review['development_and_packaging_gaps']['workspace_dependency_imports_missing_locally']}`")
    append(f"- bootstrap note: {review['development_and_packaging_gaps']['pytest_local_bootstrap']}")
    append("")
    append("## Required changes for a certifiably fully featured and certifiably fully RFC compliant package")
    append("")
    for item in review["required_changes_for_full_certification"]:
        append(f"- {item}")
    append("")
    return "\n".join(lines)


def main() -> int:
    review = build_review()
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(review, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    MD_OUT.write_text(render_markdown(review) + "\n", encoding="utf-8")
    print(json.dumps({"markdown": str(MD_OUT.relative_to(REPO_ROOT)), "json": str(JSON_OUT.relative_to(REPO_ROOT))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
