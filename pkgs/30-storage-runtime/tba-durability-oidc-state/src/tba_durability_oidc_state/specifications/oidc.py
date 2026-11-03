"""OIDC durable-state aliases and executable runtime specifications."""

from tba_storage_oidc.tables import BackchannelLogoutReplay, LogoutState

from tigrbl import deriveTableSpec
from tigrbl import makeOp
from tba_durability_oidc_state.operations.oidc_replay import (
    register_backchannel_logout_replay,
)
from tba_durability_oidc_state.operations.oidc_logout import (
    ensure_logout_for_session,
    latest_logout_for_session,
    mark_logout_channel,
    update_logout_metadata,
)

BackchannelLogoutReplayTable = BackchannelLogoutReplay
BackchannelLogoutReplayRuntimeSpec = deriveTableSpec(
    BackchannelLogoutReplayTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="register",
            handler=register_backchannel_logout_replay,
        ),
    ),
)

LogoutStateTable = LogoutState
LogoutStateRuntimeSpec = deriveTableSpec(
    LogoutStateTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="latest_for_session",
            handler=latest_logout_for_session,
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="update_metadata",
            handler=update_logout_metadata,
            arity="member",
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="mark_channel",
            handler=mark_logout_channel,
            arity="member",
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="ensure_for_session",
            handler=ensure_logout_for_session,
        ),
    ),
)

__all__ = [
    "BackchannelLogoutReplayRuntimeSpec",
    "BackchannelLogoutReplayTable",
    "LogoutStateRuntimeSpec",
    "LogoutStateTable",
]
