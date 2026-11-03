"""Token-record table alias and executable runtime specification."""

from tba_storage_token.tables import TokenRecord

from tigrbl import deriveTableSpec
from tigrbl import makeOp
from tba_durability_token.operations.tokens import (
    introspect_token_record,
    mark_refresh_token_rotated,
    persist_issued_token,
    read_token_record,
    revoke_refresh_token_family,
)

TokenRecordTable = TokenRecord
TokenRecordRuntimeSpec = deriveTableSpec(
    TokenRecordTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="persist_issued",
            handler=persist_issued_token,
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            alias="get_by_hash",
            handler=read_token_record,
            tx_scope="read_only",
            persist="skip",
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="mark_rotated",
            handler=mark_refresh_token_rotated,
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="revoke_family",
            handler=revoke_refresh_token_family,
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="introspect",
            handler=introspect_token_record,
        ),
    ),
)

__all__ = ["TokenRecordRuntimeSpec", "TokenRecordTable"]
