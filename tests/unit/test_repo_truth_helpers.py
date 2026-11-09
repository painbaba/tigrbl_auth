from __future__ import annotations

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback
    import tomli as tomllib
from pathlib import Path

import yaml

from tba_operator_identity.repo_truth import (
    evaluate_tier4_bundle,
    has_install_matrix_workflow,
    has_release_gate_workflow,
    package_version,
)


ROOT = Path(__file__).resolve().parents[2]


def test_package_version_matches_pyproject_project_version() -> None:
    manifest = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert package_version(ROOT) == manifest["project"]["version"]


def test_workflow_role_detection_accepts_actual_entrypoint_topology(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    workflows = repo_root / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    (workflows / "_certification-matrix.yml").write_text("name: matrix\n", encoding="utf-8")
    (workflows / "_contracts.yml").write_text("name: contracts\n", encoding="utf-8")
    (workflows / "_evidence.yml").write_text("name: evidence\n", encoding="utf-8")
    (workflows / "_release-bundle.yml").write_text("name: release bundle\n", encoding="utf-8")
    (workflows / "main.yml").write_text(
        "jobs:\n"
        "  certification-matrix:\n"
        "    uses: ./.github/workflows/_certification-matrix.yml\n"
        "  evidence:\n"
        "    uses: ./.github/workflows/_evidence.yml\n",
        encoding="utf-8",
    )
    (workflows / "release.yml").write_text(
        "jobs:\n"
        "  contracts:\n"
        "    uses: ./.github/workflows/_contracts.yml\n"
        "  certification-matrix:\n"
        "    uses: ./.github/workflows/_certification-matrix.yml\n"
        "  evidence:\n"
        "    uses: ./.github/workflows/_evidence.yml\n"
        "  release-bundle:\n"
        "    uses: ./.github/workflows/_release-bundle.yml\n",
        encoding="utf-8",
    )

    assert has_install_matrix_workflow(repo_root) is True
    assert has_release_gate_workflow(repo_root) is True


def test_evaluate_tier4_bundle_rejects_non_independent_fixture_bundle() -> None:
    bundle_root = ROOT / "compliance" / "evidence" / "tier4" / "bundles" / "browser--browser-rp"
    manifest = yaml.safe_load((bundle_root / "manifest.yaml").read_text(encoding="utf-8"))

    passed, failures, details = evaluate_tier4_bundle(bundle_root, manifest)

    assert passed is False
    assert "peer operator is not independent" in failures
    assert "bundle manifest contains validation failures" in failures
    assert details["validation_failure_count"] > 0
