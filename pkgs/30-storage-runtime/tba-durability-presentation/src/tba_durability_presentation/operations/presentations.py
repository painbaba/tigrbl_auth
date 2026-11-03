"""Durable presentation lifecycle operations."""

from tba_primitives_identity.persistence import reject_sensitive_raw_fields
from tba_storage_presentation.tables import PresentationConsent, PresentationReplay, PresentationTransaction

from tigrbl import provideTableHandler

begin_presentation = provideTableHandler(
    PresentationTransaction, payload_validator=reject_sensitive_raw_fields
)
record_presentation_consent = provideTableHandler(
    PresentationConsent, payload_validator=reject_sensitive_raw_fields
)
reserve_presentation_replay = provideTableHandler(
    PresentationReplay, payload_validator=reject_sensitive_raw_fields
)

__all__ = [
    "begin_presentation",
    "record_presentation_consent",
    "reserve_presentation_replay",
]
