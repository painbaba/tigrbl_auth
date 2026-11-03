"""Attestation table aliases and executable runtime specifications."""

from tba_storage_attestation.tables import AttestationEvidence, AttestationReferenceManifest, AttestationResult

from tigrbl import deriveTableSpec
from tigrbl import makeOp
from tba_durability_attestation.operations.attestation import (
    publish_reference_material,
    record_attestation_evidence,
    record_attestation_result,
)

AttestationEvidenceTable = AttestationEvidence
AttestationResultTable = AttestationResult
AttestationReferenceManifestTable = AttestationReferenceManifest

AttestationEvidenceRuntimeSpec = deriveTableSpec(
    AttestationEvidenceTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="record_evidence",
            handler=record_attestation_evidence,
        ),
    ),
)
AttestationResultRuntimeSpec = deriveTableSpec(
    AttestationResultTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="record_appraisal_result",
            handler=record_attestation_result,
        ),
    ),
)
AttestationReferenceManifestRuntimeSpec = deriveTableSpec(
    AttestationReferenceManifestTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="publish_reference_material",
            handler=publish_reference_material,
        ),
    ),
)

__all__ = [
    "AttestationEvidenceRuntimeSpec",
    "AttestationEvidenceTable",
    "AttestationReferenceManifestRuntimeSpec",
    "AttestationReferenceManifestTable",
    "AttestationResultRuntimeSpec",
    "AttestationResultTable",
]
