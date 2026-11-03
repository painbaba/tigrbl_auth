"""Durable workload-reference and credential-entitlement operations."""

from tba_primitives_identity.persistence import reject_sensitive_raw_fields
from tba_storage_workload_identity.tables import WorkloadCredentialEntitlement, WorkloadReferenceBinding
from tigrbl import provideTableHandler

bind_workload_reference = provideTableHandler(
    WorkloadReferenceBinding, payload_validator=reject_sensitive_raw_fields
)
grant_workload_credential_entitlement = provideTableHandler(
    WorkloadCredentialEntitlement, payload_validator=reject_sensitive_raw_fields
)
__all__ = ["bind_workload_reference", "grant_workload_credential_entitlement"]
