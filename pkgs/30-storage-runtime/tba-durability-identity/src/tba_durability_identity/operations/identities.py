"""Durable identity lookup and local-password state operations."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tigrbl import (
    database_from_context,
    field_value,
    first_table_record,
    payload_from_context,
    read_table_record,
    record_identifier,
    update_table_record,
)


async def lookup_identity_by_identifier(ctx: Mapping[str, Any]) -> Any:
    from tba_storage_principals.tables import User

    identifier = str(payload_from_context(ctx).get("identifier") or "").strip()
    if not identifier:
        return None
    db = database_from_context(ctx)
    row = await first_table_record(User, db, {"username": identifier})
    if row is None:
        row = await first_table_record(User, db, {"email": identifier})
    if row is None or not bool(field_value(row, "is_active", True)):
        return None
    return row


def _identity_id(ctx: Mapping[str, Any]) -> Any:
    payload = payload_from_context(ctx)
    path = ctx.get("path_params") or {}
    return (
        payload.get("identity_id")
        or payload.get("user_id")
        or payload.get("id")
        or path.get("id")
    )


async def replace_password_hash(ctx: Mapping[str, Any]) -> Any:
    from tba_storage_principals.tables import User

    payload = payload_from_context(ctx)
    encoded_hash = payload.get("password_hash")
    if encoded_hash in {None, b"", ""}:
        raise ValueError("password_hash is required")
    db = database_from_context(ctx)
    row = await read_table_record(User, db, _identity_id(ctx))
    if row is None:
        return None
    return await update_table_record(
        User,
        db,
        record_identifier(row),
        {
            "password_hash": encoded_hash,
            "must_change_password": bool(payload.get("must_change_password", False)),
        },
    )


async def set_identity_enabled(ctx: Mapping[str, Any]) -> Any:
    from tba_storage_principals.tables import User

    payload = payload_from_context(ctx)
    db = database_from_context(ctx)
    row = await read_table_record(User, db, _identity_id(ctx))
    if row is None:
        return None
    return await update_table_record(
        User,
        db,
        record_identifier(row),
        {"is_active": bool(payload.get("enabled", True))},
    )


__all__ = [
    "lookup_identity_by_identifier",
    "replace_password_hash",
    "set_identity_enabled",
]
