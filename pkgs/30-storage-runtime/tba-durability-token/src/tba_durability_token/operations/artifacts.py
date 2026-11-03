"""Durable protected-artifact reference and possession-proof replay operations."""

from tba_primitives_identity.persistence import reject_sensitive_raw_fields
from tba_storage_token.tables import PossessionProofReplay, ProtectedArtifactReference
from tigrbl import provideTableHandler

register_protected_artifact_reference = provideTableHandler(
    ProtectedArtifactReference, payload_validator=reject_sensitive_raw_fields
)
reserve_possession_proof_replay = provideTableHandler(
    PossessionProofReplay, payload_validator=reject_sensitive_raw_fields
)
__all__ = ["register_protected_artifact_reference", "reserve_possession_proof_replay"]
