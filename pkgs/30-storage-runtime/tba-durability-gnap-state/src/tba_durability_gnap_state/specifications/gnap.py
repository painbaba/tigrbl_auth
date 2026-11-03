"""GNAP durable-state aliases and executable runtime specifications."""

from tba_storage_gnap.tables import GnapClientInstance, GnapContinuation, GnapGrant, GnapInteraction

from tigrbl import deriveTableSpec
from tigrbl import makeOp
from tba_durability_gnap_state.operations.gnap import (
    complete_gnap_interaction,
    create_gnap_grant,
    read_gnap_continuation,
    read_gnap_grant,
    record_gnap_client_instance,
    record_gnap_continuation,
    record_gnap_interaction,
    rotate_gnap_continuation,
    update_gnap_grant,
)

GnapClientInstanceTable = GnapClientInstance
GnapClientInstanceRuntimeSpec = deriveTableSpec(
    GnapClientInstanceTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="record_client_instance",
            handler=record_gnap_client_instance,
        ),
    ),
)

GnapGrantTable = GnapGrant
GnapGrantRuntimeSpec = deriveTableSpec(
    GnapGrantTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="create_grant",
            handler=create_gnap_grant,
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            alias="read_grant",
            handler=read_gnap_grant,
            tx_scope="read_only",
            persist="skip",
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="update_grant",
            handler=update_gnap_grant,
        ),
    ),
)

GnapContinuationTable = GnapContinuation
GnapContinuationRuntimeSpec = deriveTableSpec(
    GnapContinuationTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="record_continuation",
            handler=record_gnap_continuation,
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            alias="read_continuation",
            handler=read_gnap_continuation,
            tx_scope="read_only",
            persist="skip",
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="rotate_continuation",
            handler=rotate_gnap_continuation,
        ),
    ),
)

GnapInteractionTable = GnapInteraction
GnapInteractionRuntimeSpec = deriveTableSpec(
    GnapInteractionTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="record_interaction",
            handler=record_gnap_interaction,
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="complete_interaction",
            handler=complete_gnap_interaction,
        ),
    ),
)

__all__ = [
    "GnapClientInstanceRuntimeSpec",
    "GnapClientInstanceTable",
    "GnapContinuationRuntimeSpec",
    "GnapContinuationTable",
    "GnapGrantRuntimeSpec",
    "GnapGrantTable",
    "GnapInteractionRuntimeSpec",
    "GnapInteractionTable",
]
