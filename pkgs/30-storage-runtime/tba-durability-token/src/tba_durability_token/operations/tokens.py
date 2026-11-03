"""Durable profiled-token lifecycle operations."""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Mapping
from typing import Any

from tba_primitives_identity.clock import utc_now
from tba_primitives_identity.digests import token_hash

from tigrbl import (
    create_table_record,
    database_from_context,
    field_value,
    first_table_record,
    list_table_records,
    payload_from_context,
    update_table_record,
)


def _to_uuid(value: Any) -> uuid.UUID | None:
    if value is None or value == "" or value is False:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return None


def _to_datetime(value: Any) -> dt.datetime | None:
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return (
            value if value.tzinfo is not None else value.replace(tzinfo=dt.timezone.utc)
        )
    try:
        return dt.datetime.fromtimestamp(int(value), tz=dt.timezone.utc)
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def _to_epoch(value: dt.datetime | None) -> int | None:
    if value is None:
        return None
    normalized = (
        value if value.tzinfo is not None else value.replace(tzinfo=dt.timezone.utc)
    )
    return int(normalized.timestamp())


async def persist_issued_token(ctx: Mapping[str, Any]) -> Any:
    """Idempotently persist one explicitly profiled issued token."""

    from tba_storage_token.tables import TokenRecord

    payload = dict(payload_from_context(ctx))
    claims = dict(payload.get("claims") or {})
    digest = payload["token_hash"]
    db = database_from_context(ctx)
    row = await first_table_record(TokenRecord, db, {"token_hash": digest})
    now = utc_now()
    record = {
        "token_hash": digest,
        "jti": claims.get("jti") or field_value(row, "jti"),
        "token_kind": payload.get("token_kind")
        or claims.get("kind")
        or claims.get("typ")
        or field_value(row, "token_kind", "access"),
        "token_profile": payload.get("token_profile")
        or field_value(row, "token_profile"),
        "audience_digest": payload.get("audience_digest")
        or field_value(row, "audience_digest"),
        "sender_constraint_kind": payload.get("sender_constraint_kind")
        or field_value(row, "sender_constraint_kind"),
        "credential_or_grant_reference": payload.get("credential_or_grant_reference")
        or field_value(row, "credential_or_grant_reference"),
        "token_type_hint": payload.get("token_type_hint")
        or field_value(row, "token_type_hint"),
        "token_status": payload.get("token_status")
        or field_value(row, "token_status", "active"),
        "refresh_family_id": payload.get("refresh_family_id")
        or field_value(row, "refresh_family_id"),
        "refresh_parent_hash": payload.get("refresh_parent_hash")
        or field_value(row, "refresh_parent_hash"),
        "refresh_successor_hash": payload.get("refresh_successor_hash")
        or field_value(row, "refresh_successor_hash"),
        "active": payload.get("active")
        if payload.get("active") is not None
        else field_value(row, "active", True),
        "subject": str(
            claims.get("sub")
            or payload.get("subject")
            or field_value(row, "subject", "unknown")
        ),
        "tenant_id": _to_uuid(
            claims.get("tid")
            or payload.get("tenant_id")
            or field_value(row, "tenant_id")
        ),
        "client_id": _to_uuid(
            claims.get("client_id")
            or claims.get("azp")
            or payload.get("client_id")
            or field_value(row, "client_id")
        ),
        "scope": claims.get("scope")
        or payload.get("scope")
        or field_value(row, "scope"),
        "issuer": claims.get("iss")
        or payload.get("issuer")
        or field_value(row, "issuer"),
        "kid": claims.get("kid") or payload.get("kid") or field_value(row, "kid"),
        "key_version": payload.get("key_version") or field_value(row, "key_version"),
        "audience": claims.get("aud")
        or payload.get("audience")
        or field_value(row, "audience"),
        "claims": claims or field_value(row, "claims"),
        "issued_at": payload.get("issued_at")
        or _to_datetime(claims.get("iat"))
        or field_value(row, "issued_at")
        or now,
        "expires_at": payload.get("expires_at")
        or _to_datetime(claims.get("exp"))
        or field_value(row, "expires_at"),
        "used_at": payload.get("used_at") or field_value(row, "used_at"),
        "reuse_detected_at": payload.get("reuse_detected_at")
        or field_value(row, "reuse_detected_at"),
    }
    if row is None:
        return await create_table_record(TokenRecord, db, record)
    return await update_table_record(
        TokenRecord,
        db,
        field_value(row, "id"),
        record,
    )


async def read_token_record(ctx: Mapping[str, Any]) -> Any:
    """Read one token record by a supplied digest without mutating lifecycle state."""

    from tba_storage_token.tables import TokenRecord

    payload = payload_from_context(ctx)
    digest = payload.get("token_hash")
    if not digest:
        raise ValueError("token_hash is required")
    return await first_table_record(
        TokenRecord,
        database_from_context(ctx),
        {"token_hash": digest},
    )


async def mark_refresh_token_rotated(ctx: Mapping[str, Any]) -> Any:
    from tba_storage_token.tables import TokenRecord

    payload = dict(payload_from_context(ctx))
    db = database_from_context(ctx)
    row = await first_table_record(
        TokenRecord,
        db,
        {"token_hash": payload["token_hash"]},
    )
    if row is None:
        return None
    return await update_table_record(
        TokenRecord,
        db,
        field_value(row, "id"),
        {
            "active": False,
            "token_status": "rotated",
            "used_at": payload.get("used_at") or utc_now(),
            "refresh_successor_hash": payload.get("successor_hash"),
            "revoked_reason": payload.get("reason")
            or field_value(row, "revoked_reason")
            or "refresh_rotated",
        },
    )


async def revoke_refresh_token_family(ctx: Mapping[str, Any]) -> list[Any]:
    from tba_storage_token.tables import TokenRecord

    payload = dict(payload_from_context(ctx))
    db = database_from_context(ctx)
    rows = await list_table_records(
        TokenRecord,
        db,
        {"refresh_family_id": payload["refresh_family_id"]},
    )
    now = utc_now()
    updated: list[Any] = []
    for row in rows:
        record = {
            "active": False,
            "token_status": "revoked",
            "revoked_at": field_value(row, "revoked_at") or now,
            "revoked_reason": payload.get("reason")
            or field_value(row, "revoked_reason")
            or "refresh_family_revoked",
        }
        if (
            payload.get("reuse_token_hash")
            and field_value(row, "token_hash") == payload["reuse_token_hash"]
        ):
            record["reuse_detected_at"] = field_value(row, "reuse_detected_at") or now
        updated.append(
            await update_table_record(
                TokenRecord,
                db,
                field_value(row, "id"),
                record,
            )
        )
    return updated


async def introspect_token_record(ctx: Mapping[str, Any]) -> dict[str, Any]:
    from tba_storage_token.tables import TokenRecord

    payload = dict(payload_from_context(ctx))
    digest = payload.get("token_hash") or token_hash(payload["token"])
    db = database_from_context(ctx)
    now = utc_now()
    row = await first_table_record(TokenRecord, db, {"token_hash": digest})
    if row is None:
        return {"active": False}
    expires_at = field_value(row, "expires_at")
    if expires_at is not None:
        expiry = (
            expires_at
            if expires_at.tzinfo is not None
            else expires_at.replace(tzinfo=dt.timezone.utc)
        )
        if expiry <= now:
            await update_table_record(
                TokenRecord,
                db,
                field_value(row, "id"),
                {
                    "active": False,
                    "token_status": "expired",
                    "revoked_reason": "expired",
                },
            )
            return {"active": False}
    if field_value(row, "revoked_at") is not None or not bool(
        field_value(row, "active")
    ):
        await update_table_record(
            TokenRecord,
            db,
            field_value(row, "id"),
            {"active": False, "last_introspected_at": now},
        )
        return {"active": False}
    await update_table_record(
        TokenRecord,
        db,
        field_value(row, "id"),
        {"last_introspected_at": now},
    )
    response = dict(field_value(row, "claims") or {})
    response.setdefault("sub", field_value(row, "subject"))
    if field_value(row, "scope"):
        response.setdefault("scope", field_value(row, "scope"))
    if field_value(row, "client_id") is not None:
        response.setdefault("client_id", str(field_value(row, "client_id")))
    if field_value(row, "issuer"):
        response.setdefault("iss", field_value(row, "issuer"))
    exp = _to_epoch(expires_at)
    if exp is not None:
        response.setdefault("exp", exp)
    response["active"] = True
    return response


__all__ = [
    "introspect_token_record",
    "mark_refresh_token_rotated",
    "persist_issued_token",
    "read_token_record",
    "revoke_refresh_token_family",
]
