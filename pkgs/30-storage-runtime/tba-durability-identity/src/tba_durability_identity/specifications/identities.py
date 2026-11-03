"""User identity table alias and executable runtime specification."""

from tba_storage_principals.tables import User

from tigrbl import deriveTableSpec
from tigrbl import makeOp
from tba_durability_identity.operations.identities import (
    lookup_identity_by_identifier,
    replace_password_hash,
    set_identity_enabled,
)


UserTable = User
UserRuntimeSpec = deriveTableSpec(
    UserTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            alias="lookup_by_identifier",
            handler=lookup_identity_by_identifier,
            tx_scope="read_only",
            persist="skip",
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="replace_password_hash",
            handler=replace_password_hash,
            arity="member",
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="set_enabled",
            handler=set_identity_enabled,
            arity="member",
        ),
    ),
)


__all__ = ["UserRuntimeSpec", "UserTable"]
