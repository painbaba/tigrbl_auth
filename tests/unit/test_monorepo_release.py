from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.monorepo_release import (
    TESTKIT_ROOT_EXTRAS,
    _local_dependency_closure,
    _materialize_testkit_interop_artifacts,
    _root_project_package,
    discover_packages,
)


SCRIPT = ROOT / "scripts" / "monorepo_release.py"


def test_deprecated_release_requires_explicit_package_selection(monkeypatch, capsys) -> None:
    from argparse import Namespace
    from scripts import monorepo_release as release

    name = "tba-provider-jose-swarmauri"
    assert name not in {p.name for p in release.discover_packages()}
    assert release._find_package(name).path.parts[1] == "deprecated"
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    release.cmd_release_matrix(Namespace(package=name))
    output = json.loads(capsys.readouterr().out)
    cells = json.loads(output["matrix"])
    assert output["count"] == "1"
    release.cmd_resolve_release_index(Namespace(package=name, index=cells[0]["index"]))
    resolved = json.loads(capsys.readouterr().out)
    assert resolved["name"] == name
    assert resolved["path"] == "pkgs/deprecated/" + name
    release.cmd_release_matrix(Namespace(package="all"))
    all_cells = json.loads(json.loads(capsys.readouterr().out)["matrix"])
    assert len(all_cells) == len(release.discover_packages())


def test_release_indices_round_trip_without_package_metadata() -> None:
    """Public credential names must not cross the secret-scanned job boundary."""
    selected = "tba-concrete-credential-password"
    matrix = subprocess.check_output(
        [sys.executable, str(SCRIPT), "release-matrix", "--package", selected],
        cwd=ROOT, text=True,
    )
    output = json.loads(matrix)
    cells = json.loads(output["matrix"])
    assert output["count"] == "1"
    assert len(cells) == 1 and set(cells[0]) == {"index"}
    assert isinstance(cells[0]["index"], int)
    assert selected not in matrix and "password" not in matrix
    resolved = json.loads(subprocess.check_output(
        [sys.executable, str(SCRIPT), "resolve-release-index", "--index",
         str(cells[0]["index"]), "--package", selected],
        cwd=ROOT, text=True,
    ))
    package = next(p for p in discover_packages() if p.name == selected)
    assert resolved == package.as_cell()
    all_output = json.loads(subprocess.check_output(
        [sys.executable, str(SCRIPT), "release-matrix"], cwd=ROOT, text=True,
    ))
    all_cells = json.loads(all_output["matrix"])
    assert int(all_output["count"]) == len(all_cells) == len(discover_packages())
    assert [cell["index"] for cell in all_cells] == list(range(len(all_cells)))
    for index, name in [(-1, selected), (len(discover_packages()), selected),
                        (cells[0]["index"], "tba-primitives-identity")]:
        rejected = subprocess.run(
            [sys.executable, str(SCRIPT), "resolve-release-index", "--index", str(index),
             "--package", name], cwd=ROOT, text=True, capture_output=True,
        )
        assert rejected.returncode != 0

REMOVED_HELPER_PACKAGES = {
    "tba-runtime-authorization-policy-abac-administrator",
    "tba-runtime-authorization-policy-delegated-administrator",
    "tba-runtime-authorization-policy-engine",
    "tba-runtime-authorization-policy-rbac-administrator",
    "tba-runtime-authorization-policy-service-identity-registry",
    "tba-protocol-oauth-protected-resource-dpop-cnf-binding-validator",
    "tba-protocol-oauth-protected-resource-introspection-client",
    "tba-protocol-oauth-protected-resource-jwks-cache",
    "tba-protocol-oauth-protected-resource-mtls-cnf-binding-validator",
    "tba-protocol-oauth-protected-resource-sender-constraint-validator",
}


def test_monorepo_release_discovers_split_packages() -> None:
    packages = {item.name: item for item in discover_packages()}

    # The package-per-concrete-object architecture intentionally grows this
    # inventory; discovery must include at least the original split boundary.
    assert len(packages) >= 78
    assert "tba-workspace" not in packages
    assert REMOVED_HELPER_PACKAGES.isdisjoint(packages)
    assert packages["tba-contracts-identity"].path.as_posix() == "pkgs/02-contracts/tba-contracts-identity"
    assert packages["tba-bases-security-trust-domain"].path.as_posix() == "pkgs/05-bases/tba-bases-security-trust-domain"
    assert packages["tba-provider-authorization-policy-decision-engine"].path.as_posix() == (
        "pkgs/20-providers/tba-provider-authorization-policy-decision-engine"
    )
    assert packages["tba-concrete-authorization-policy-rules"].path.as_posix() == (
        "pkgs/10-concrete/tba-concrete-authorization-policy-rules"
    )
    assert all("deprecated" not in package.path.parts for package in packages.values())
    assert all(not name.startswith("tigrbl-") for name in packages)
    assert packages["tba-provider-authorization-resource-server-verifier"].path.as_posix() == (
        "pkgs/20-providers/tba-provider-authorization-resource-server-verifier"
    )
    assert packages["tba-provider-security-token-jwks-cache"].path.as_posix() == (
        "pkgs/20-providers/tba-provider-security-token-jwks-cache"
    )
    assert packages["tba-runtime-identity-storage"].path.as_posix() == (
        "pkgs/30-storage-runtime/tba-runtime-identity-storage"
    )
    assert packages["tba-runtime-authorization-policy"].path.as_posix() == "pkgs/60-runtime/tba-runtime-authorization-policy"
    assert packages["tba-runtime-identity-administration"].path.as_posix() == "pkgs/60-runtime/tba-runtime-identity-administration"
    assert packages["tba-protocol-oauth-protected-resource"].path.as_posix() == "pkgs/50-protocols/tba-protocol-oauth-protected-resource"


def test_monorepo_release_accepts_package_version_tag() -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "resolve-tag", "tba-auth==0.4.0.dev2"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert '"name": "tba-auth"' in completed.stdout
    assert '"tag": "tba-auth==0.4.0.dev2"' in completed.stdout


def test_monorepo_release_rejects_stale_version_for_split_package() -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "resolve-tag", "tba-auth==0.4.0.dev1"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    assert "does not match tba-auth pyproject version" in completed.stderr


def test_monorepo_release_builds_package_python_test_matrix() -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "test-matrix"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(completed.stdout)
    matrix = json.loads(payload["matrix"])

    assert int(payload["count"]) == len(matrix)
    assert len(matrix) >= 299
    names = {cell["name"] for cell in matrix}
    assert REMOVED_HELPER_PACKAGES.isdisjoint(names)
    assert "tba-security-token-verification" not in names
    assert "tba-provider-authorization-resource-server-verifier" in names
    assert "tba-provider-security-token-jwks-cache" in names
    assert "tba-runtime-identity-storage" in names
    assert {
        cell["python_version"]
        for cell in matrix
        if cell["name"] == "tba-provider-authorization-resource-server-verifier"
    } == {"3.10", "3.11", "3.12", "3.13", "3.14"}
    testkit_cells = [cell for cell in matrix if cell["name"] == "tba-testkit-identity"]
    assert len(testkit_cells) == 3
    assert all(cell["cross_cutting"] == "true" for cell in testkit_cells)
    assert all("tests/packages/tba-testkit-identity" in cell["package_test_paths"] for cell in testkit_cells)
    assert all("tests/integration" not in cell["package_test_paths"] for cell in testkit_cells)
    assert all("tests/interop" in cell["package_test_paths"] for cell in testkit_cells)
    assert all(cell["pytest_args"] == "--certification-lane\nall" for cell in testkit_cells)


def test_monorepo_release_filters_package_python_test_matrix() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "test-matrix",
            "--package",
            "tba-protocol-oauth",
            "--python-version",
            "3.12",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(completed.stdout)
    matrix = json.loads(payload["matrix"])

    assert payload["count"] == "1"
    assert matrix == [
        {
            "name": "tba-protocol-oauth",
            "version": "0.4.0.dev2",
            "path": "pkgs/50-protocols/tba-protocol-oauth",
            "import_root": "tba_protocol_oauth",
            "tag": "tba-protocol-oauth==0.4.0.dev2",
            "python_version": "3.12",
            "python_tag": "py312",
            "cell_id": "tba-protocol-oauth-py312",
            "workspace_source_globs": "pkgs/*/*/src\npkgs/deprecated/*/src",
            "package_test_paths": "tests/packages/tba-protocol-oauth\ntests/packages/tba_protocol_oauth",
            "pre_test_command": "",
            "pytest_args": "",
            "cross_cutting": "false",
        }
    ]


def test_monorepo_release_resolves_local_dependency_closure() -> None:
    packages = {item.name: item for item in discover_packages()}

    dependency_names = {
        item.name
        for item in _local_dependency_closure(packages["tba-app-backend-core"])
    }

    assert REMOVED_HELPER_PACKAGES.isdisjoint(dependency_names)
    assert {
        "tba-protocol-oauth",
        "tba-runtime-identity-authoring",
        "tba-contracts-identity",
        "tba-primitives-identity",
        "tba-provider-identity-jose",
        "tba-runtime-identity",
        "tba-storage-core",
        "tba-contracts-security-key-rotation-policy",
        "tba-provider-security-proof-pkce",
        "tba-provider-security-signing-pqc",
        "tba-contracts-security-trust",
        "tba-bases-claim",
        "tba-bases-protected-artifact",
        "tba-bases-signing",
    }.issubset(dependency_names)

    facade_dependency_names = {
        item.name for item in _local_dependency_closure(packages["tba-auth"])
    }
    assert "tba-protocol-oauth" in facade_dependency_names
    assert "tba-runtime-identity-authoring" in facade_dependency_names
    assert "tba-storage-core" in facade_dependency_names
    assert "tba-provider-security-token-jwks-cache" in facade_dependency_names

    api_dependency_names = {
        item.name
        for item in _local_dependency_closure(packages["tba-app-backend-developer"])
    }
    assert "tba-auth" in api_dependency_names
    assert "tba-protocol-oauth" in api_dependency_names


def test_monorepo_release_resolves_root_first_party_dependency_closure() -> None:
    root_dependency_names = {
        item.name for item in _local_dependency_closure(_root_project_package())
    }

    assert REMOVED_HELPER_PACKAGES.isdisjoint(root_dependency_names)
    assert "tba-protocol-oauth-protected-resource" in root_dependency_names
    assert "tba-provider-authorization-resource-server-verifier" in root_dependency_names
    assert "tba-provider-security-token-jwks-cache" in root_dependency_names
    assert "tba-router-administration-gate" in root_dependency_names
    assert "tba-concrete-authorization-policy-rules" in root_dependency_names
    assert "tigrbl-identity-identities-concrete" not in root_dependency_names
    assert "tba-runtime-identity-authoring" in root_dependency_names
    assert "tba-protocol-oauth" in root_dependency_names
    assert "tba-server-identity" in root_dependency_names


def test_monorepo_release_materializes_testkit_interop_templates_with_isolated_python(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], Path | None, bool]] = []

    def fake_run(args: list[str], *, cwd: Path | None = None, check: bool = False) -> None:
        calls.append((args, cwd, check))

    monkeypatch.setattr(subprocess, "run", fake_run)

    _materialize_testkit_interop_artifacts(Path(".venv/bin/python"))

    assert len(calls) == 1
    args, cwd, check = calls[0]
    assert Path(args[0]) == Path(".venv/bin/python")
    assert args[1] == "-c"
    assert "materialize_external_handoff_templates" in args[2]
    assert cwd == ROOT
    assert check is True



def test_testkit_wheel_closure_includes_local_compatibility_packages_and_extras() -> None:
    names = {
        package.name
        for package in _local_dependency_closure(
            _root_project_package(), extras=TESTKIT_ROOT_EXTRAS
        )
    }
    assert "tba-provider-security-cose" in names
    assert "tba-contracts-dns" in names
    assert "tba-profile-communications-identity-bimi" in names
