"""Carrier-neutral durable WebAuthn ceremony operations."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from tba_primitives_identity.digests import sha256_digest
from tba_storage_webauthn.tables import WebAuthnCeremony

from tigrbl import (
    create_table_record,
    database_from_context,
    field_value,
    first_table_record,
    payload_from_context,
    record_identifier,
    update_table_record,
)


def _aware(value: object, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")
    return value


async def reserve_ceremony(ctx: Mapping[str, Any], *, kind: str) -> object:
    payload = dict(payload_from_context(ctx))
    challenge = payload.pop("challenge", None)
    if not isinstance(challenge, bytes) or len(challenge) < 16:
        raise ValueError("WebAuthn challenge must contain at least 16 bytes")
    if kind not in {"registration", "authentication"}:
        raise ValueError("invalid WebAuthn ceremony kind")
    issued_at = _aware(payload.get("issued_at"), "issued_at")
    expires_at = _aware(payload.get("expires_at"), "expires_at")
    if expires_at <= issued_at:
        raise ValueError("WebAuthn ceremony must expire after it is issued")
    payload.update(
        ceremony_kind=kind,
        challenge_digest=sha256_digest(challenge),
        state="pending",
    )
    return await create_table_record(
        WebAuthnCeremony, database_from_context(ctx), payload
    )


async def reserve_registration_ceremony(ctx: Mapping[str, Any]) -> object:
    return await reserve_ceremony(ctx, kind="registration")


async def reserve_authentication_ceremony(ctx: Mapping[str, Any]) -> object:
    return await reserve_ceremony(ctx, kind="authentication")


async def load_active_ceremony(ctx: Mapping[str, Any]) -> object | None:
    payload = payload_from_context(ctx)
    ceremony_id = str(payload.get("ceremony_id", ""))
    if not ceremony_id:
        raise ValueError("ceremony_id is required")
    row = await first_table_record(
        WebAuthnCeremony,
        database_from_context(ctx),
        {"ceremony_id": ceremony_id},
    )
    if row is None or field_value(row, "state") != "pending":
        return None
    expires_at = field_value(row, "expires_at")
    if isinstance(expires_at, datetime) and expires_at <= datetime.now(timezone.utc):
        await update_table_record(
            WebAuthnCeremony,
            database_from_context(ctx),
            record_identifier(row),
            {"state": "expired"},
        )
        return None
    return row


async def consume_ceremony(ctx: Mapping[str, Any]) -> object:
    payload = payload_from_context(ctx)
    row = await load_active_ceremony(ctx)
    if row is None:
        raise PermissionError(
            "WebAuthn ceremony is missing, expired, or already consumed"
        )
    challenge = payload.get("challenge")
    if not isinstance(challenge, bytes):
        raise TypeError("verified ceremony challenge must be bytes")
    if sha256_digest(challenge) != field_value(row, "challenge_digest"):
        raise PermissionError("WebAuthn ceremony challenge mismatch")
    return await update_table_record(
        WebAuthnCeremony,
        database_from_context(ctx),
        record_identifier(row),
        {
            "state": "consumed",
            "consumed_at": datetime.now(timezone.utc),
            "bound_credential_id": payload.get("bound_credential_id"),
        },
    )


async def fail_ceremony(ctx: Mapping[str, Any]) -> object:
    payload = payload_from_context(ctx)
    row = await first_table_record(
        WebAuthnCeremony,
        database_from_context(ctx),
        {"ceremony_id": str(payload.get("ceremony_id", ""))},
    )
    if row is None:
        raise LookupError("WebAuthn ceremony not found")
    return await update_table_record(
        WebAuthnCeremony,
        database_from_context(ctx),
        record_identifier(row),
        {
            "state": "failed",
            "failure_code": str(payload.get("failure_code", "verification_failed")),
        },
    )


__all__ = [
    "consume_ceremony",
    "fail_ceremony",
    "load_active_ceremony",
    "reserve_authentication_ceremony",
    "reserve_registration_ceremony",
]
