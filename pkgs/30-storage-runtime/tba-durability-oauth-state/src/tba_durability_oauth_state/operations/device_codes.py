"""Durable device-authorization lifecycle operations."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tba_primitives_identity.clock import utc_now

from tigrbl import (
    database_from_context,
    list_table_records,
    payload_from_context,
    record_identifier,
    update_table_record,
)


async def _resolve_device_code(db: Any, payload: Mapping[str, Any]) -> Any:
    from tba_storage_oauth.tables import DeviceCode

    if payload.get("id") is not None:
        matches = await list_table_records(DeviceCode, db, {"id": payload["id"]})
    elif payload.get("device_code") is not None:
        matches = await list_table_records(
            DeviceCode,
            db,
            {"device_code": payload["device_code"]},
        )
    else:
        return None
    return matches[0] if matches else None


async def approve_device_code(ctx: Mapping[str, Any]) -> Any:
    from tba_storage_oauth.tables import DeviceCode

    payload = payload_from_context(ctx)
    db = database_from_context(ctx)
    row = await _resolve_device_code(db, payload)
    if row is None:
        return None
    return await update_table_record(
        DeviceCode,
        db,
        record_identifier(row),
        {
            "authorized": True,
            "authorized_at": payload.get("authorized_at") or utc_now(),
            "denied_at": None,
            "denial_reason": None,
            "user_id": payload.get("sub"),
            "tenant_id": payload.get("tid"),
        },
    )


async def deny_device_code(ctx: Mapping[str, Any]) -> Any:
    from tba_storage_oauth.tables import DeviceCode

    payload = payload_from_context(ctx)
    db = database_from_context(ctx)
    row = await _resolve_device_code(db, payload)
    if row is None:
        return None
    return await update_table_record(
        DeviceCode,
        db,
        record_identifier(row),
        {
            "authorized": False,
            "denied_at": payload.get("denied_at") or utc_now(),
            "denial_reason": payload.get("reason") or "access_denied",
        },
    )


__all__ = ["approve_device_code", "deny_device_code"]
