"""Durable registered public-key credential operations."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from tba_storage_webauthn.tables import CredentialWebAuthnPasskey

from tigrbl import (
    create_table_record,
    database_from_context,
    first_table_record,
    list_table_records,
    payload_from_context,
    record_identifier,
    update_table_record,
)


async def insert_public_key_credential(ctx: Mapping[str, Any]) -> object:
    payload = dict(payload_from_context(ctx))
    for name in (
        "credential_external_id",
        "credential_public_key_cose",
        "rp_id",
        "principal_id",
    ):
        if payload.get(name) in {None, "", b""}:
            raise ValueError(f"{name} is required")
    payload.setdefault("webauthn_credential_id", payload["credential_external_id"])
    payload.setdefault("public_key", bytes(payload["credential_public_key_cose"]).hex())
    payload.setdefault("credential_id", str(payload["credential_external_id"]))
    payload.setdefault("status", "active")
    return await create_table_record(
        CredentialWebAuthnPasskey, database_from_context(ctx), payload
    )


async def find_public_key_credential(ctx: Mapping[str, Any]) -> object | None:
    payload = payload_from_context(ctx)
    return await first_table_record(
        CredentialWebAuthnPasskey,
        database_from_context(ctx),
        {
            "credential_external_id": payload.get("credential_external_id"),
            "rp_id": payload.get("rp_id"),
        },
    )


async def find_discoverable_credentials(ctx: Mapping[str, Any]) -> list[object]:
    payload = payload_from_context(ctx)
    return await list_table_records(
        CredentialWebAuthnPasskey,
        database_from_context(ctx),
        {
            "tenant_id": payload.get("tenant_id"),
            "rp_id": payload.get("rp_id"),
            "discoverable": True,
            "status": "active",
        },
    )


async def update_assertion_state(ctx: Mapping[str, Any]) -> object:
    payload = payload_from_context(ctx)
    row = await find_public_key_credential(ctx)
    if row is None:
        raise LookupError("public-key credential not found")
    sign_count = payload.get("sign_count")
    if (
        isinstance(sign_count, bool)
        or not isinstance(sign_count, int)
        or sign_count < 0
    ):
        raise ValueError("signature counter must be a non-negative integer")
    backup_eligible = bool(
        payload.get("backup_eligible", getattr(row, "backup_eligible", False))
    )
    backup_state = bool(payload.get("backup_state", False))
    if backup_state and not backup_eligible:
        raise ValueError("backup state requires backup eligibility")
    return await update_table_record(
        CredentialWebAuthnPasskey,
        database_from_context(ctx),
        record_identifier(row),
        {
            "sign_count": sign_count,
            "backup_eligible": backup_eligible,
            "backup_state": backup_state,
            "last_used_at": payload.get("used_at") or datetime.now(timezone.utc),
        },
    )


async def list_principal_public_key_credentials(ctx: Mapping[str, Any]) -> list[object]:
    payload = payload_from_context(ctx)
    return await list_table_records(
        CredentialWebAuthnPasskey,
        database_from_context(ctx),
        {
            "tenant_id": payload.get("tenant_id"),
            "principal_id": payload.get("principal_id"),
        },
    )


async def rename_public_key_credential(ctx: Mapping[str, Any]) -> object:
    payload = payload_from_context(ctx)
    row = await find_public_key_credential(ctx)
    if row is None:
        raise LookupError("public-key credential not found")
    return await update_table_record(
        CredentialWebAuthnPasskey,
        database_from_context(ctx),
        record_identifier(row),
        {"display_name": str(payload.get("display_name", "")).strip() or None},
    )


async def revoke_public_key_credential(ctx: Mapping[str, Any]) -> object:
    row = await find_public_key_credential(ctx)
    if row is None:
        raise LookupError("public-key credential not found")
    return await update_table_record(
        CredentialWebAuthnPasskey,
        database_from_context(ctx),
        record_identifier(row),
        {"status": "revoked", "revoked_at": datetime.now(timezone.utc)},
    )


__all__ = [
    "find_discoverable_credentials",
    "find_public_key_credential",
    "insert_public_key_credential",
    "list_principal_public_key_credentials",
    "rename_public_key_credential",
    "revoke_public_key_credential",
    "update_assertion_state",
]
