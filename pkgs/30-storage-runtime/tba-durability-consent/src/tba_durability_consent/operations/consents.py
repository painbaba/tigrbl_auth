"""Durable consent lifecycle operations."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any

from tba_primitives_identity.clock import utc_now

from tigrbl import (
    database_from_context,
    field_value,
    list_table_records,
    payload_from_context,
    update_table_record,
)


def _to_uuid(value: Any) -> uuid.UUID | None:
    if value in {None, ""}:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def _principal_filters(ctx: Mapping[str, Any]) -> dict[str, Any]:
    payload = payload_from_context(ctx)
    filters: dict[str, Any] = {}
    user_id = _to_uuid(payload.get("user_id"))
    tenant_id = _to_uuid(payload.get("tenant_id"))
    if user_id is not None:
        filters["user_id"] = user_id
    if tenant_id is not None:
        filters["tenant_id"] = tenant_id
    return filters


async def list_consents_for_user(ctx: Mapping[str, Any]) -> list[Any]:
    from tba_storage_consent.tables import Consent

    return await list_table_records(
        Consent,
        database_from_context(ctx),
        _principal_filters(ctx),
    )


async def revoke_consent_for_user(ctx: Mapping[str, Any]) -> Any:
    from tba_storage_consent.tables import Consent

    filters = _principal_filters(ctx)
    path = ctx.get("path_params") or {}
    payload = payload_from_context(ctx)
    consent_id = _to_uuid(path.get("id") or path.get("consent_id") or payload.get("id"))
    if consent_id is None:
        return None
    filters["id"] = consent_id
    rows = await list_table_records(
        Consent,
        database_from_context(ctx),
        filters,
    )
    if not rows:
        return None
    row = rows[0]
    return await update_table_record(
        Consent,
        database_from_context(ctx),
        field_value(row, "id"),
        {
            "state": "revoked",
            "revoked_at": field_value(row, "revoked_at") or utc_now(),
        },
    )


async def revoke_consents_for_client(ctx: Mapping[str, Any]) -> list[Any]:
    from tba_storage_consent.tables import Consent

    filters = _principal_filters(ctx)
    path = ctx.get("path_params") or {}
    payload = payload_from_context(ctx)
    client_id = _to_uuid(
        path.get("client_id") or path.get("id") or payload.get("client_id")
    )
    if client_id is None:
        return []
    filters["client_id"] = client_id
    db = database_from_context(ctx)
    rows = await list_table_records(Consent, db, filters)
    now = utc_now()
    return [
        await update_table_record(
            Consent,
            db,
            field_value(row, "id"),
            {
                "state": "revoked",
                "revoked_at": field_value(row, "revoked_at") or now,
            },
        )
        for row in rows
    ]


__all__ = [
    "list_consents_for_user",
    "revoke_consent_for_user",
    "revoke_consents_for_client",
]
