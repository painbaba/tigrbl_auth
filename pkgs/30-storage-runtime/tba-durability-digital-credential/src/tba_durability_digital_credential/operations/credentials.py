"""Durable credential lifecycle operations."""

from tba_primitives_identity.persistence import reject_sensitive_raw_fields
from tba_storage_digital_credential.tables import CredentialIssuanceTransaction, CredentialOffer, CredentialStatusEntry

from tigrbl import provideTableHandler

create_offer = provideTableHandler(
    CredentialOffer, payload_validator=reject_sensitive_raw_fields
)
begin_issuance = provideTableHandler(
    CredentialIssuanceTransaction, payload_validator=reject_sensitive_raw_fields
)
set_credential_status = provideTableHandler(
    CredentialStatusEntry, payload_validator=reject_sensitive_raw_fields
)

__all__ = ["begin_issuance", "create_offer", "set_credential_status"]
