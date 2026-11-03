"""Durable audit-event operations and compatibility adapters."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tigrbl import (
    create_table_record,
    database_from_context,
    field_value,
    list_table_records,
    payload_from_context,
)


async def append_audit_event_record(ctx: Mapping[str, Any]) -> Any:
    from tba_storage_audit.tables import AuditEvent
    from tba_storage_tenancy.tables import Tenant

    db = database_from_context(ctx)
    payload = dict(payload_from_context(ctx))
    if payload.get("tenant_id") is None:
        tenants = await list_table_records(Tenant, db, {})
        if tenants:
            payload["tenant_id"] = field_value(tenants[0], "id")
    return await create_table_record(AuditEvent, db, payload)


async def list_audit_event_records(ctx: Mapping[str, Any]) -> list[Any]:
    from tba_storage_audit.tables import AuditEvent

    filters = {
        key: value
        for key, value in dict(payload_from_context(ctx)).items()
        if value is not None
    }
    return await list_table_records(AuditEvent, database_from_context(ctx), filters)


async def append_audit_event_async(*, db: Any, **payload: Any) -> Any:
    """Append using an explicitly injected transaction/session."""

    return await append_audit_event_record({"payload": payload, "db": db})


__all__ = [
    "append_audit_event_async",
    "append_audit_event_record",
    "list_audit_event_records",
]
