"""Client table alias and executable runtime specification."""

from tba_storage_oauth.tables import Client

from tigrbl import deriveTableSpec
from tigrbl import makeOp
from tba_durability_identity.operations.clients import (
    disable_client,
    enable_client,
    lookup_client,
    replace_client_secret_hash,
)


ClientTable = Client
ClientRuntimeSpec = deriveTableSpec(
    ClientTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            alias="lookup_client",
            handler=lookup_client,
            tx_scope="read_only",
            persist="skip",
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="enable",
            handler=enable_client,
            arity="member",
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="disable",
            handler=disable_client,
            arity="member",
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="rotate_secret_hash",
            handler=replace_client_secret_hash,
            arity="member",
        ),
    ),
)


__all__ = ["ClientRuntimeSpec", "ClientTable"]
