"""OAuth durable-state aliases and executable runtime specifications."""

from tba_storage_oauth.tables import AuthCode, ClientRegistration, DeviceCode, PushedAuthorizationRequest, RevokedToken

from tigrbl import deriveTableSpec
from tigrbl import makeOp
from tba_durability_oauth_state.operations.oauth_state import (
    create_client_registration,
    disable_client_registration,
    is_token_hash_revoked,
    persist_authorization_code,
    persist_pushed_authorization_request,
    read_client_registration,
    record_revoked_token_hash,
    update_client_registration,
    upsert_client_registration,
)
from tba_durability_oauth_state.operations.device_codes import (
    approve_device_code,
    deny_device_code,
)

AuthCodeTable = AuthCode
AuthCodeRuntimeSpec = deriveTableSpec(
    AuthCodeTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="authorize",
            handler=persist_authorization_code,
        ),
    ),
)

ClientRegistrationTable = ClientRegistration
ClientRegistrationRuntimeSpec = deriveTableSpec(
    ClientRegistrationTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="register",
            handler=create_client_registration,
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            alias="get_registration",
            handler=read_client_registration,
            tx_scope="read_only",
            persist="skip",
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="update_registration",
            handler=update_client_registration,
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="disable_registration",
            handler=disable_client_registration,
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="upsert",
            handler=upsert_client_registration,
        ),
    ),
)

DeviceCodeTable = DeviceCode
DeviceCodeRuntimeSpec = deriveTableSpec(
    DeviceCodeTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="approve",
            handler=approve_device_code,
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="deny",
            handler=deny_device_code,
        ),
    ),
)

PushedAuthorizationRequestTable = PushedAuthorizationRequest
PushedAuthorizationRequestRuntimeSpec = deriveTableSpec(
    PushedAuthorizationRequestTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="push_authorization_request",
            handler=persist_pushed_authorization_request,
        ),
    ),
)

RevokedTokenTable = RevokedToken
RevokedTokenRuntimeSpec = deriveTableSpec(
    RevokedTokenTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="record_hash",
            handler=record_revoked_token_hash,
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="is_hash_revoked",
            handler=is_token_hash_revoked,
        ),
    ),
)

__all__ = [
    "AuthCodeRuntimeSpec",
    "AuthCodeTable",
    "ClientRegistrationRuntimeSpec",
    "ClientRegistrationTable",
    "DeviceCodeRuntimeSpec",
    "DeviceCodeTable",
    "PushedAuthorizationRequestRuntimeSpec",
    "PushedAuthorizationRequestTable",
    "RevokedTokenRuntimeSpec",
    "RevokedTokenTable",
]
