"""WebAuthn table aliases and executable durable specifications."""

from tba_storage_webauthn.tables import CredentialWebAuthnPasskey, WebAuthnAttestationRecord, WebAuthnCeremony, WebAuthnRelyingParty

from tigrbl import deriveTableSpec
from tigrbl import makeOp
from tba_durability_webauthn.operations.webauthn_ceremonies import (
    consume_ceremony,
    fail_ceremony,
    load_active_ceremony,
    reserve_authentication_ceremony,
    reserve_registration_ceremony,
)
from tba_durability_webauthn.operations.webauthn_credentials import (
    find_discoverable_credentials,
    find_public_key_credential,
    insert_public_key_credential,
    list_principal_public_key_credentials,
    rename_public_key_credential,
    revoke_public_key_credential,
    update_assertion_state,
)
from tba_durability_webauthn.operations.webauthn_relying_parties import (
    resolve_relying_party_configuration,
)

WebAuthnCeremonyTable = WebAuthnCeremony
WebAuthnRelyingPartyTable = WebAuthnRelyingParty
WebAuthnCredentialTable = CredentialWebAuthnPasskey
WebAuthnAttestationRecordTable = WebAuthnAttestationRecord

WebAuthnCeremonyRuntimeSpec = deriveTableSpec(
    WebAuthnCeremonyTable,
    ops=tuple(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias=name,
            handler=handler,
        )
        for name, handler in (
            ("reserve_registration_ceremony", reserve_registration_ceremony),
            ("reserve_authentication_ceremony", reserve_authentication_ceremony),
            ("load_active_ceremony", load_active_ceremony),
            ("consume_ceremony", consume_ceremony),
            ("fail_ceremony", fail_ceremony),
        )
    ),
)
WebAuthnCredentialRuntimeSpec = deriveTableSpec(
    WebAuthnCredentialTable,
    ops=tuple(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias=name,
            handler=handler,
        )
        for name, handler in (
            ("insert_public_key_credential", insert_public_key_credential),
            ("find_public_key_credential", find_public_key_credential),
            ("find_discoverable_credentials", find_discoverable_credentials),
            ("update_assertion_state", update_assertion_state),
            (
                "list_principal_public_key_credentials",
                list_principal_public_key_credentials,
            ),
            ("rename_public_key_credential", rename_public_key_credential),
            ("revoke_public_key_credential", revoke_public_key_credential),
        )
    ),
)
WebAuthnRelyingPartyRuntimeSpec = deriveTableSpec(
    WebAuthnRelyingPartyTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            alias="resolve_relying_party_configuration",
            handler=resolve_relying_party_configuration,
            tx_scope="read",
            persist="skip",
        ),
    ),
)
WebAuthnAttestationRecordRuntimeSpec = deriveTableSpec(WebAuthnAttestationRecordTable)

__all__ = [name for name in globals() if name.endswith(("RuntimeSpec", "Table"))]
