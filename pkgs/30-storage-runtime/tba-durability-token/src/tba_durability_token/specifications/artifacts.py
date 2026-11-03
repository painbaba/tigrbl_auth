"""Protected artifact and possession-proof replay runtime specifications."""

from tba_storage_token.tables import PossessionProofReplay, ProtectedArtifactReference
from tigrbl import deriveTableSpec, makeOp
from tba_durability_token.operations.artifacts import (
    register_protected_artifact_reference,
    reserve_possession_proof_replay,
)

ProtectedArtifactReferenceTable = ProtectedArtifactReference
PossessionProofReplayTable = PossessionProofReplay
ProtectedArtifactReferenceRuntimeSpec = deriveTableSpec(
    ProtectedArtifactReferenceTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="register_protected_artifact_reference",
            handler=register_protected_artifact_reference,
        ),
    ),
)
PossessionProofReplayRuntimeSpec = deriveTableSpec(
    PossessionProofReplayTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="reserve_possession_proof_replay",
            handler=reserve_possession_proof_replay,
        ),
    ),
)
__all__ = [
    "PossessionProofReplayRuntimeSpec",
    "PossessionProofReplayTable",
    "ProtectedArtifactReferenceRuntimeSpec",
    "ProtectedArtifactReferenceTable",
]
