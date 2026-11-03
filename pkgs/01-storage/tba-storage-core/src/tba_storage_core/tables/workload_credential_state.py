"""Compatibility exports of domain-owned storage tables."""

from tba_storage_workload_identity.tables import WorkloadReferenceBinding, WorkloadCredentialEntitlement
from tba_storage_token.tables import ProtectedArtifactReference, PossessionProofReplay

__all__ = ['WorkloadReferenceBinding', 'WorkloadCredentialEntitlement', 'ProtectedArtifactReference', 'PossessionProofReplay']
