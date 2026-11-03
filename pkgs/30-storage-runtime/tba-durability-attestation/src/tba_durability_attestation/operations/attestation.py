"""Durable attestation and reference-material operations."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tba_storage_attestation.tables import AttestationEndorsement, AttestationEvidence, AttestationReferenceManifest, AttestationReferenceValue, AttestationResult
from tba_primitives_identity.persistence import reject_sensitive_raw_fields

from tigrbl import (
    provideTableHandler,
    database_from_context,
    maybe_await,
    payload_from_context,
)

record_attestation_evidence = provideTableHandler(
    AttestationEvidence, payload_validator=reject_sensitive_raw_fields
)
record_attestation_result = provideTableHandler(
    AttestationResult, payload_validator=reject_sensitive_raw_fields
)


def make_attestation_appraisal_recorder(
    *,
    db: Any,
    evidence_id: str,
    artifact_locator: str,
    evidence_digest: str,
    issuer: str | None = None,
    policy_id: str | None = None,
    evidence_recorder: Any = None,
    result_recorder: Any = None,
):
    """Bind caller-owned durable state to the capability recorder signature."""

    evidence_recorder = evidence_recorder or record_attestation_evidence
    result_recorder = result_recorder or record_attestation_result

    async def record(verified_evidence: Any, appraisal_result: Any) -> Any:
        evidence = verified_evidence.evidence
        envelope = verified_evidence.envelope.envelope
        await evidence_recorder(
            {
                "payload": {
                    "evidence_id": evidence_id,
                    "profile": evidence.profile,
                    "format": envelope.format.value,
                    "issuer": issuer,
                    "artifact_locator": artifact_locator,
                    "evidence_digest": evidence_digest,
                },
                "db": db,
            }
        )
        return await result_recorder(
            {
                "payload": {
                    "evidence_id": evidence_id,
                    "policy_id": policy_id,
                    "trusted": appraisal_result.trusted,
                    "reason": appraisal_result.reason,
                    "result_claims": dict(appraisal_result.claims),
                },
                "db": db,
            }
        )

    return record


async def publish_reference_material(ctx: Mapping[str, Any]) -> Mapping[str, object]:
    """Stage a manifest and its material in one caller-owned transaction."""

    payload = payload_from_context(ctx)
    reject_sensitive_raw_fields(payload)
    manifest = payload.get("manifest")
    values = payload.get("reference_values", ())
    endorsements = payload.get("endorsements", ())
    if not isinstance(manifest, Mapping):
        raise TypeError("reference material requires a manifest mapping")
    if not isinstance(values, (list, tuple)) or not all(
        isinstance(value, Mapping) for value in values
    ):
        raise TypeError("reference_values must be a sequence of mappings")
    if not isinstance(endorsements, (list, tuple)) or not all(
        isinstance(value, Mapping) for value in endorsements
    ):
        raise TypeError("endorsements must be a sequence of mappings")

    db = database_from_context(ctx)
    manifest_id = manifest.get("manifest_id")
    if not manifest_id:
        raise ValueError("reference manifest requires manifest_id")
    manifest_record = await maybe_await(
        AttestationReferenceManifest.handlers.create.core(
            AttestationReferenceManifest, manifest, db
        )
    )
    value_records = []
    for value in values:
        material = {"manifest_id": manifest_id, **dict(value)}
        value_records.append(
            await maybe_await(
                AttestationReferenceValue.handlers.create.core(
                    AttestationReferenceValue, material, db
                )
            )
        )
    endorsement_records = []
    for endorsement in endorsements:
        endorsement_records.append(
            await maybe_await(
                AttestationEndorsement.handlers.create.core(
                    AttestationEndorsement, endorsement, db
                )
            )
        )
    return {
        "manifest": manifest_record,
        "reference_values": tuple(value_records),
        "endorsements": tuple(endorsement_records),
    }


__all__ = [
    "make_attestation_appraisal_recorder",
    "publish_reference_material",
    "record_attestation_evidence",
    "record_attestation_result",
]
