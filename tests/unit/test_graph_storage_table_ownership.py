from __future__ import annotations

import importlib
import ast
from pathlib import Path

from sqlalchemy import UniqueConstraint


def test_storage_core_deep_imports_preserve_domain_table_identity() -> None:
    tables = importlib.import_module("tba_storage_core.tables")
    metadata = tables.TABLE_MODELS[0].__table__.metadata
    before = set(metadata.tables)
    root = Path(tables.__file__).parent
    for source in root.rglob("*.py"):
        tree = ast.parse(source.read_text(encoding="utf-8-sig"))
        assert not any(isinstance(node, ast.ClassDef) for node in ast.walk(tree)), source
        relative = source.relative_to(root).with_suffix("").parts
        if relative[-1] == "__init__":
            relative = relative[:-1]
        module = importlib.import_module(".".join(("tba_storage_core", "tables", *relative)))
        for name in getattr(module, "__all__", ()):
            canonical = tables.TABLE_MODEL_BY_NAME.get(name)
            if canonical is not None:
                assert getattr(module, name) is canonical, (module.__name__, name)
                assert getattr(module, name).__table__ is canonical.__table__
    assert set(metadata.tables) == before


def _unique_columns(model: type) -> set[tuple[str, ...]]:
    uniques: set[tuple[str, ...]] = set()
    for constraint in model.__table__.constraints:
        if isinstance(constraint, UniqueConstraint):
            uniques.add(tuple(column.name for column in constraint.columns))
    return uniques


def test_graph_storage_exports_concrete_graph_tables_not_generic_graph_registry() -> None:
    tables = importlib.import_module("tba_storage_core.tables")

    for abstract_name in ("GraphBase", "GraphNodeBase", "GraphEdgeBase"):
        assert abstract_name not in tables.TABLE_MODEL_BY_NAME

    for concrete_name in (
        "AuthorityDerivationGraph",
        "AuthorityDerivationGraphNode",
        "AuthorityDerivationGraphEdge",
        "TrustFederationGraph",
        "TrustFederationGraphNode",
        "TrustFederationGraphEdge",
    ):
        assert concrete_name in tables.TABLE_MODEL_BY_NAME
        assert getattr(tables, concrete_name) is tables.TABLE_MODEL_BY_NAME[concrete_name]


def test_graph_edge_uniqueness_is_edge_key_scoped_not_src_dst_kind() -> None:
    tables = importlib.import_module("tba_storage_core.tables")

    for model in (tables.AuthorityDerivationGraphEdge, tables.TrustFederationGraphEdge):
        uniques = _unique_columns(model)
        assert ("graph_id", "edge_key") in uniques
        assert ("src_id", "dst_id", "kind") not in uniques

    for model in (tables.AuthorityDerivationGraphNode, tables.TrustFederationGraphNode):
        assert ("graph_id", "node_key") in _unique_columns(model)


def test_graph_algorithms_are_storage_neutral_and_layer_30_specs_bind_tables() -> None:
    tables = importlib.import_module("tba_storage_core.tables")
    authority_concrete = importlib.import_module("tba_concrete_authority_graph")
    trust_concrete = importlib.import_module("tba_concrete_trust_federation_graph")
    authority = importlib.import_module("tba_durability_authorization_policy_authority_derivation_graph")
    trust = importlib.import_module("tba_durability_identity_administration_trust_federation_graph")

    assert not hasattr(authority_concrete.AuthorityDerivationGraph, "graph_table")
    assert not hasattr(trust_concrete.TrustFederationGraph, "graph_table")
    assert authority.AuthorityDerivationGraphRuntimeSpec.model is tables.AuthorityDerivationGraph
    assert authority.AuthorityDerivationGraphNodeRuntimeSpec.model is tables.AuthorityDerivationGraphNode
    assert authority.AuthorityDerivationGraphEdgeRuntimeSpec.model is tables.AuthorityDerivationGraphEdge
    assert trust.TrustFederationGraphRuntimeSpec.model is tables.TrustFederationGraph
    assert trust.TrustFederationGraphNodeRuntimeSpec.model is tables.TrustFederationGraphNode
    assert trust.TrustFederationGraphEdgeRuntimeSpec.model is tables.TrustFederationGraphEdge


def test_graph_storage_does_not_introduce_repository_wrappers() -> None:
    forbidden_names = {
        "GraphRepository",
        "StorageGraphRepository",
        "AuthorityGraphRepository",
        "TrustGraphRepository",
    }
    modules = (
        importlib.import_module("tba_storage_core.tables"),
        importlib.import_module("tba_durability_authorization_policy_authority_derivation_graph"),
        importlib.import_module("tba_durability_identity_administration_trust_federation_graph"),
    )

    for module in modules:
        for name in forbidden_names:
            assert not hasattr(module, name)
