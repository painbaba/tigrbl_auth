"""Consent table alias and executable runtime specification."""

from tba_storage_consent.tables import Consent

from tigrbl import deriveTableSpec
from tigrbl import makeOp
from tba_durability_consent.operations.consents import (
    list_consents_for_user,
    revoke_consent_for_user,
    revoke_consents_for_client,
)

ConsentTable = Consent
ConsentRuntimeSpec = deriveTableSpec(
    ConsentTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="list_for_user",
            handler=list_consents_for_user,
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="revoke_for_user",
            handler=revoke_consent_for_user,
            arity="member",
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="revoke_for_client",
            handler=revoke_consents_for_client,
        ),
    ),
)

__all__ = ["ConsentRuntimeSpec", "ConsentTable"]
