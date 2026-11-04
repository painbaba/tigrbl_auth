from __future__ import annotations

import ast
import tomllib
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
LAYER = ROOT / "pkgs" / "30-storage-runtime"
TAXONOMY = yaml.safe_load(
    (ROOT / "architecture" / "durability-package-taxonomy.yaml").read_text(
        encoding="utf-8"
    )
)


def test_durability_packages_use_declared_domain_storage_owners() -> None:
    for package in LAYER.glob("tba-durability-*"):
        project = tomllib.loads((package / "pyproject.toml").read_text())["project"]
        dependencies = project.get("dependencies", [])
        assert any(value.startswith("tba-storage-") for value in dependencies), package
        assert not any(value.startswith("tba-storage-core") for value in dependencies), package
        declared = {value.split("==")[0].replace("-", "_") for value in dependencies}
        for source in (package / "src").rglob("*.py"):
            for imported in _imports(source):
                assert not imported.startswith("tba_storage_core"), source
                if imported.startswith("tba_storage_"):
                    assert imported.split(".")[0] in declared, (source, imported)


def _imports(source: Path) -> set[str]:
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def test_every_layer_30_package_has_one_explicit_disposition() -> None:
    actual = {
        path.name for path in LAYER.iterdir() if (path / "pyproject.toml").exists()
    }
    declared = {
        *TAXONOMY["canonical_packages"],
        *TAXONOMY["compatibility_packages"],
    }
    assert actual == declared


def test_canonical_durability_packages_have_no_higher_layer_imports() -> None:
    forbidden = (
        "tba_router_",
        "tba_protocol_",
        "tba_protocol_oauth_protected_resource",
        "tba_runtime_identity",
        "tba_server_identity",
        "tba_runtime_identity_storage",
    )
    packages = list(TAXONOMY["canonical_packages"])
    violations: list[str] = []
    for package in packages:
        for source in (LAYER / package).rglob("*.py"):
            for imported in _imports(source):
                if imported.startswith(forbidden):
                    violations.append(f"{source.relative_to(ROOT)} -> {imported}")
    assert violations == []


def test_canonical_durability_packages_do_not_define_repository_wrappers() -> None:
    forbidden_suffixes = ("Repository", "Store", "UnitOfWork", "Service")
    packages = list(TAXONOMY["canonical_packages"])
    violations: list[str] = []
    for package in packages:
        for source in (LAYER / package).rglob("*.py"):
            tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name.endswith(
                    forbidden_suffixes
                ):
                    violations.append(f"{source.relative_to(ROOT)}:{node.lineno}")
    assert violations == []


def test_legacy_operation_and_spec_paths_are_identity_preserving_facades() -> None:
    from tba_runtime_identity_storage.ops.webauthn_ceremonies import (
        consume_ceremony as legacy_consume,
    )
    from tba_runtime_identity_storage.tables.webauthn import (
        WebAuthnCeremonyRuntimeSpec as legacy_spec,
    )
    from tba_durability_webauthn.operations.webauthn_ceremonies import (
        consume_ceremony,
    )
    from tba_durability_webauthn.specifications.webauthn import (
        WebAuthnCeremonyRuntimeSpec,
    )

    assert legacy_consume is consume_ceremony
    assert legacy_spec is WebAuthnCeremonyRuntimeSpec
    assert any(operation.alias == "consume_ceremony" for operation in legacy_spec.ops)


def test_engine_construction_is_owned_by_layer_30() -> None:
    canonical = (
        LAYER
        / "tba-runtime-identity-storage/src/tba_runtime_identity_storage/engine.py"
    ).read_text(encoding="utf-8")
    compatibility = (
        ROOT
        / "pkgs/60-runtime/tba-runtime-identity/src/tba_runtime_identity/engine.py"
    ).read_text(encoding="utf-8")
    assert "build_engine(" in canonical
    assert "tba_runtime_identity_storage.engine" in compatibility
    assert "build_engine(" not in compatibility


def test_identity_storage_runtime_uses_direct_tba_packages() -> None:
    package = LAYER / "tba-runtime-identity-storage"
    facade_imports: list[str] = []
    for source in (package / "src").rglob("*.py"):
        for imported in _imports(source):
            if imported == "tigrbl" or imported.startswith("tigrbl."):
                facade_imports.append(f"{source.relative_to(ROOT)} -> {imported}")

    manifest = (package / "pyproject.toml").read_text(encoding="utf-8")

    assert facade_imports == []
    assert '"tigrbl-concrete==0.4.5.dev8"' in manifest
    assert '"tigrbl-core==0.4.5.dev6"' in manifest
    assert '"tigrbl==0.4.5.dev8"' not in manifest
