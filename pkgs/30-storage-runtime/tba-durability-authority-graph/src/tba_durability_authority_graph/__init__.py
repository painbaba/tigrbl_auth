"""Durable authority-graph table operations and specifications."""

from tba_storage_authority_graph.tables import AuthorityDerivationGraph as AuthorityGraphTable, AuthorityDerivationGraphEdge as AuthorityGraphEdgeTable, AuthorityDerivationGraphNode as AuthorityGraphNodeTable
from tigrbl import (
    provideTableHandler,
    deriveTableSpec,
    makeOp,
)

record_authority_graph = provideTableHandler(AuthorityGraphTable)
add_authority_graph_node = provideTableHandler(AuthorityGraphNodeTable)
add_authority_graph_edge = provideTableHandler(AuthorityGraphEdgeTable)

AuthorityGraphRuntimeSpec = deriveTableSpec(
    AuthorityGraphTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="record_graph",
            handler=record_authority_graph,
        ),
    ),
)
AuthorityGraphNodeRuntimeSpec = deriveTableSpec(
    AuthorityGraphNodeTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="add_node",
            handler=add_authority_graph_node,
        ),
    ),
)
AuthorityGraphEdgeRuntimeSpec = deriveTableSpec(
    AuthorityGraphEdgeTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="add_edge",
            handler=add_authority_graph_edge,
        ),
    ),
)

__all__ = [name for name in globals() if not name.startswith("_")]
