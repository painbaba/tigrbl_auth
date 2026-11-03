"""Presentation table aliases and executable runtime specifications."""

from tba_storage_presentation.tables import PresentationConsent, PresentationReplay, PresentationTransaction

from tigrbl import deriveTableSpec
from tigrbl import makeOp
from tba_durability_presentation.operations.presentations import (
    begin_presentation,
    record_presentation_consent,
    reserve_presentation_replay,
)

PresentationTransactionTable = PresentationTransaction
PresentationConsentTable = PresentationConsent
PresentationReplayTable = PresentationReplay

PresentationTransactionRuntimeSpec = deriveTableSpec(
    PresentationTransactionTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="begin_presentation",
            handler=begin_presentation,
        ),
    ),
)
PresentationConsentRuntimeSpec = deriveTableSpec(
    PresentationConsentTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="record_consent",
            handler=record_presentation_consent,
        ),
    ),
)
PresentationReplayRuntimeSpec = deriveTableSpec(
    PresentationReplayTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="reserve_replay",
            handler=reserve_presentation_replay,
        ),
    ),
)

__all__ = [
    "PresentationConsentRuntimeSpec",
    "PresentationConsentTable",
    "PresentationReplayRuntimeSpec",
    "PresentationReplayTable",
    "PresentationTransactionRuntimeSpec",
    "PresentationTransactionTable",
]
