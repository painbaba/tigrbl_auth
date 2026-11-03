"""Authentication-session table alias and executable runtime specification."""

from tba_storage_oauth.tables import AuthSession

from tigrbl import deriveTableSpec
from tigrbl import makeOp
from tba_durability_session.operations.sessions import (
    bind_session_client,
    get_active_session,
    rotate_session_cookie_secret,
    terminate_session,
    touch_session,
)

AuthSessionTable = AuthSession
AuthSessionRuntimeSpec = deriveTableSpec(
    AuthSessionTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="terminate",
            handler=terminate_session,
            arity="member",
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="touch",
            handler=touch_session,
            arity="member",
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="get_active",
            handler=get_active_session,
            arity="member",
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="rotate_cookie_secret",
            handler=rotate_session_cookie_secret,
            arity="member",
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="bind_client",
            handler=bind_session_client,
            arity="member",
        ),
    ),
)

__all__ = ["AuthSessionRuntimeSpec", "AuthSessionTable"]
