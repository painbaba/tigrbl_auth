"""Credential table aliases and executable runtime specifications."""

from tba_storage_digital_credential.tables import CredentialIssuanceTransaction, CredentialOffer, CredentialStatusEntry

from tigrbl import deriveTableSpec
from tigrbl import makeOp
from tba_durability_digital_credential.operations.credentials import (
    begin_issuance,
    create_offer,
    set_credential_status,
)

CredentialOfferTable = CredentialOffer
CredentialIssuanceTransactionTable = CredentialIssuanceTransaction
CredentialStatusEntryTable = CredentialStatusEntry

CredentialOfferRuntimeSpec = deriveTableSpec(
    CredentialOfferTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="create_offer",
            handler=create_offer,
        ),
    ),
)
CredentialIssuanceTransactionRuntimeSpec = deriveTableSpec(
    CredentialIssuanceTransactionTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="begin_issuance",
            handler=begin_issuance,
        ),
    ),
)
CredentialStatusEntryRuntimeSpec = deriveTableSpec(
    CredentialStatusEntryTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="set_credential_status",
            handler=set_credential_status,
        ),
    ),
)

__all__ = [
    "CredentialIssuanceTransactionRuntimeSpec",
    "CredentialIssuanceTransactionTable",
    "CredentialOfferRuntimeSpec",
    "CredentialOfferTable",
    "CredentialStatusEntryRuntimeSpec",
    "CredentialStatusEntryTable",
]
