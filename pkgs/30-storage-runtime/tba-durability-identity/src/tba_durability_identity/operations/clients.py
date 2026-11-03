"""Durable client lookup and lifecycle operations."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from tigrbl import (
    database_from_context,
    payload_from_context,
    read_table_record,
    record_identifier,
    update_table_record,
)


def _client_id(ctx: Mapping[str, Any]) -> Any:
    payload = payload_from_context(ctx)
    path = ctx.get("path_params") or {}
    value = payload.get("client_id") or payload.get("id") or path.get("id")
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return value


async def lookup_client(ctx: Mapping[str, Any]) -> Any:
    from tba_storage_oauth.tables import Client

    client_id = _client_id(ctx)
    if client_id in {None, ""}:
        return None
    return await read_table_record(Client, database_from_context(ctx), client_id)


async def set_client_enabled(ctx: Mapping[str, Any]) -> Any:
    from tba_storage_oauth.tables import Client

    payload = payload_from_context(ctx)
    client_id = _client_id(ctx)
    db = database_from_context(ctx)
    row = await read_table_record(Client, db, client_id)
    if row is None:
        return None
    return await update_table_record(
        Client,
        db,
        record_identifier(row),
        {"is_active": bool(payload.get("enabled", True))},
    )


async def enable_client(ctx: Mapping[str, Any]) -> Any:
    return await set_client_enabled(
        {**dict(ctx), "payload": {**dict(payload_from_context(ctx)), "enabled": True}}
    )


async def disable_client(ctx: Mapping[str, Any]) -> Any:
    return await set_client_enabled(
        {**dict(ctx), "payload": {**dict(payload_from_context(ctx)), "enabled": False}}
    )


async def replace_client_secret_hash(ctx: Mapping[str, Any]) -> Any:
    from tba_storage_oauth.tables import Client

    payload = payload_from_context(ctx)
    encoded_hash = payload.get("client_secret_hash")
    if encoded_hash in {None, b"", ""}:
        raise ValueError("client_secret_hash is required")
    client_id = _client_id(ctx)
    db = database_from_context(ctx)
    row = await read_table_record(Client, db, client_id)
    if row is None:
        return None
    return await update_table_record(
        Client,
        db,
        record_identifier(row),
        {"client_secret_hash": encoded_hash},
    )


__all__ = [
    "disable_client",
    "enable_client",
    "lookup_client",
    "replace_client_secret_hash",
    "set_client_enabled",
]
