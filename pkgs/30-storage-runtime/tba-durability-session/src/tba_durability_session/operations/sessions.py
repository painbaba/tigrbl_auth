"""Durable authentication-session lifecycle operations."""

from __future__ import annotations

import datetime as dt
from collections.abc import Mapping
from typing import Any

from tba_primitives_identity.clock import utc_now

from tigrbl import (
    database_from_context,
    field_value,
    payload_from_context,
    read_table_record,
    update_table_record,
)


def _session_id(ctx: Mapping[str, Any]) -> Any:
    payload = payload_from_context(ctx)
    path = ctx.get("path_params") or {}
    return payload.get("session_id") or payload.get("id") or path.get("id")


async def terminate_session(ctx: Mapping[str, Any]) -> Any:
    from tba_storage_oauth.tables import AuthSession

    db = database_from_context(ctx)
    payload = dict(payload_from_context(ctx))
    session_id = _session_id(ctx)
    row = await read_table_record(AuthSession, db, session_id)
    if row is None:
        return None
    now = utc_now()
    return await update_table_record(
        AuthSession,
        db,
        session_id,
        {
            "session_state": payload.get("session_state") or "terminated",
            "ended_at": field_value(row, "ended_at") or now,
            "logout_reason": payload.get("reason")
            or field_value(row, "logout_reason")
            or "logout",
        },
    )


async def touch_session(ctx: Mapping[str, Any]) -> Any:
    from tba_storage_oauth.tables import AuthSession

    db = database_from_context(ctx)
    session_id = _session_id(ctx)
    if await read_table_record(AuthSession, db, session_id) is None:
        return None
    return await update_table_record(
        AuthSession,
        db,
        session_id,
        {"last_seen_at": utc_now()},
    )


async def get_active_session(ctx: Mapping[str, Any]) -> Any:
    from tba_storage_oauth.tables import AuthSession

    db = database_from_context(ctx)
    session_id = _session_id(ctx)
    row = await read_table_record(AuthSession, db, session_id)
    if row is None:
        return None
    if field_value(row, "ended_at") is not None or str(
        field_value(row, "session_state")
    ).lower() in {"terminated", "ended", "revoked"}:
        return None
    expires_at = field_value(row, "expires_at")
    if expires_at is not None:
        expiry = (
            expires_at
            if expires_at.tzinfo is not None
            else expires_at.replace(tzinfo=dt.timezone.utc)
        )
        if expiry <= utc_now():
            await update_table_record(
                AuthSession,
                db,
                session_id,
                {
                    "session_state": "expired",
                    "ended_at": field_value(row, "ended_at") or utc_now(),
                },
            )
            return None
    return row


async def rotate_session_cookie_secret(ctx: Mapping[str, Any]) -> Any:
    from tba_storage_oauth.tables import AuthSession

    db = database_from_context(ctx)
    payload = dict(payload_from_context(ctx))
    session_id = _session_id(ctx)
    row = await read_table_record(AuthSession, db, session_id)
    if row is None:
        return None
    now = utc_now()
    return await update_table_record(
        AuthSession,
        db,
        session_id,
        {
            "cookie_secret_hash": payload.get("cookie_secret_hash"),
            "cookie_rotated_at": now,
            "cookie_issued_at": field_value(row, "cookie_issued_at") or now,
            "last_seen_at": now,
        },
    )


async def bind_session_client(ctx: Mapping[str, Any]) -> Any:
    from tba_storage_oauth.tables import AuthSession

    db = database_from_context(ctx)
    payload = dict(payload_from_context(ctx))
    session_id = _session_id(ctx)
    if await read_table_record(AuthSession, db, session_id) is None:
        return None
    return await update_table_record(
        AuthSession,
        db,
        session_id,
        {"client_id": payload.get("client_id"), "last_seen_at": utc_now()},
    )


__all__ = [
    "bind_session_client",
    "get_active_session",
    "rotate_session_cookie_secret",
    "terminate_session",
    "touch_session",
]
