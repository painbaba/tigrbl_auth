"""Delegation table aliases and executable runtime specifications."""

from tba_storage_delegation.tables import DelegationGrant, DelegationGrantEdge, DelegationGrantProof, DelegationGrantTokenLink

from tigrbl import deriveTableSpec
from tigrbl import makeOp
from tba_durability_delegation.operations.delegation import (
    activate_grant,
    create_grant,
    deactivate_grant_children,
    expire_grant,
    inspect_grant,
    link_delegation_token,
    link_grant_edge,
    list_grants,
    list_tokens_for_grant,
    persist_delegation_provenance,
    replace_grant,
    revoke_grant,
)


DelegationGrantTable = DelegationGrant
DelegationGrantEdgeTable = DelegationGrantEdge
DelegationGrantProofTable = DelegationGrantProof
DelegationGrantTokenLinkTable = DelegationGrantTokenLink

DelegationGrantRuntimeSpec = deriveTableSpec(
    DelegationGrantTable,
    ops=tuple(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias=alias,
            handler=handler,
        )
        for alias, handler in (
            ("create_grant", create_grant),
            ("inspect_grant", inspect_grant),
            ("list_grants", list_grants),
            ("activate_grant", activate_grant),
            ("expire_grant", expire_grant),
            ("replace_grant", replace_grant),
            ("revoke_grant", revoke_grant),
        )
    ),
)
DelegationGrantEdgeRuntimeSpec = deriveTableSpec(
    DelegationGrantEdgeTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="link_edge",
            handler=link_grant_edge,
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="deactivate_children",
            handler=deactivate_grant_children,
        ),
    ),
)
DelegationGrantProofRuntimeSpec = deriveTableSpec(
    DelegationGrantProofTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="persist_provenance",
            handler=persist_delegation_provenance,
        ),
    ),
)
DelegationGrantTokenLinkRuntimeSpec = deriveTableSpec(
    DelegationGrantTokenLinkTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="link_token",
            handler=link_delegation_token,
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="list_for_grant",
            handler=list_tokens_for_grant,
        ),
    ),
)


__all__ = [
    "DelegationGrantEdgeRuntimeSpec",
    "DelegationGrantEdgeTable",
    "DelegationGrantProofRuntimeSpec",
    "DelegationGrantProofTable",
    "DelegationGrantRuntimeSpec",
    "DelegationGrantTable",
    "DelegationGrantTokenLinkRuntimeSpec",
    "DelegationGrantTokenLinkTable",
]
