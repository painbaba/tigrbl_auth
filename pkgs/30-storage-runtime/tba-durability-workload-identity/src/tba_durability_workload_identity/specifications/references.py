"""Workload reference and entitlement table runtime specifications."""

from tba_storage_workload_identity.tables import WorkloadCredentialEntitlement, WorkloadReferenceBinding
from tigrbl import deriveTableSpec, makeOp
from tba_durability_workload_identity.operations.references import (
    bind_workload_reference,
    grant_workload_credential_entitlement,
)

WorkloadReferenceBindingTable = WorkloadReferenceBinding
WorkloadCredentialEntitlementTable = WorkloadCredentialEntitlement
WorkloadReferenceBindingRuntimeSpec = deriveTableSpec(
    WorkloadReferenceBindingTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="bind_workload_reference",
            handler=bind_workload_reference,
        ),
    ),
)
WorkloadCredentialEntitlementRuntimeSpec = deriveTableSpec(
    WorkloadCredentialEntitlementTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="grant_workload_credential_entitlement",
            handler=grant_workload_credential_entitlement,
        ),
    ),
)
__all__ = [
    "WorkloadCredentialEntitlementRuntimeSpec",
    "WorkloadCredentialEntitlementTable",
    "WorkloadReferenceBindingRuntimeSpec",
    "WorkloadReferenceBindingTable",
]
