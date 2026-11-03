"""Durable trust-federation graph table operations and specifications."""

from tba_storage_trust_federation_graph.tables import TrustFederationGraph as TrustFederationGraphTable, TrustFederationGraphEdge as TrustFederationGraphEdgeTable, TrustFederationGraphNode as TrustFederationGraphNodeTable
from tigrbl import (
    provideTableHandler,
    deriveTableSpec,
    makeOp,
)

record_trust_federation_graph = provideTableHandler(TrustFederationGraphTable)
add_trust_federation_graph_node = provideTableHandler(TrustFederationGraphNodeTable)
add_trust_federation_graph_edge = provideTableHandler(TrustFederationGraphEdgeTable)

TrustFederationGraphRuntimeSpec = deriveTableSpec(
    TrustFederationGraphTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="record_graph",
            handler=record_trust_federation_graph,
        ),
    ),
)
TrustFederationGraphNodeRuntimeSpec = deriveTableSpec(
    TrustFederationGraphNodeTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="add_node",
            handler=add_trust_federation_graph_node,
        ),
    ),
)
TrustFederationGraphEdgeRuntimeSpec = deriveTableSpec(
    TrustFederationGraphEdgeTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="add_edge",
            handler=add_trust_federation_graph_edge,
        ),
    ),
)

__all__ = [name for name in globals() if not name.startswith("_")]
