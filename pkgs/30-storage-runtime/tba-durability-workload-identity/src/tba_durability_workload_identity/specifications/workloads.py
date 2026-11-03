"""Workload table aliases and executable runtime specifications."""

from tba_storage_workload_identity.tables import SpiffeTrustBundle, SvidRecord

from tigrbl import deriveTableSpec
from tigrbl import makeOp
from tba_durability_workload_identity.operations.workloads import (
    activate_spiffe_trust_bundle,
    record_svid,
    record_workload_credential,
)

SvidRecordTable = SvidRecord
SpiffeTrustBundleTable = SpiffeTrustBundle

SvidRecordRuntimeSpec = deriveTableSpec(
    SvidRecordTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="record_workload_credential",
            handler=record_workload_credential,
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="record_svid",
            handler=record_svid,
        ),
    ),
)
SpiffeTrustBundleRuntimeSpec = deriveTableSpec(
    SpiffeTrustBundleTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="activate_trust_bundle",
            handler=activate_spiffe_trust_bundle,
        ),
    ),
)

__all__ = [
    "SpiffeTrustBundleRuntimeSpec",
    "SpiffeTrustBundleTable",
    "SvidRecordRuntimeSpec",
    "SvidRecordTable",
]
