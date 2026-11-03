"""Carrier-neutral durable GNAP grant-state operations."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tigrbl import (
    create_table_record,
    database_from_context,
    field_value,
    first_table_record,
    payload_from_context,
    update_table_record,
)


async def record_gnap_client_instance(ctx: Mapping[str, Any]) -> Any:
    from tba_storage_gnap.tables import GnapClientInstance

    db = database_from_context(ctx)
    payload = dict(payload_from_context(ctx))
    instance_id = payload.get("instance_id")
    if not isinstance(instance_id, str) or not instance_id:
        raise ValueError("GNAP client instance requires instance_id")
    row = await first_table_record(GnapClientInstance, db, {"instance_id": instance_id})
    if row is None:
        return await create_table_record(GnapClientInstance, db, payload)
    return await update_table_record(
        GnapClientInstance, db, field_value(row, "id"), payload
    )


async def create_gnap_grant(ctx: Mapping[str, Any]) -> Any:
    from tba_storage_gnap.tables import GnapGrant

    payload = dict(payload_from_context(ctx))
    for name in ("grant_id", "client_instance_id", "access_request"):
        if payload.get(name) is None or payload.get(name) == "":
            raise ValueError(f"GNAP grant requires {name}")
    return await create_table_record(GnapGrant, database_from_context(ctx), payload)


async def read_gnap_grant(ctx: Mapping[str, Any]) -> Any:
    from tba_storage_gnap.tables import GnapGrant

    payload = payload_from_context(ctx)
    return await first_table_record(
        GnapGrant, database_from_context(ctx), {"grant_id": payload["grant_id"]}
    )


async def update_gnap_grant(ctx: Mapping[str, Any]) -> Any:
    from tba_storage_gnap.tables import GnapGrant

    db = database_from_context(ctx)
    payload = dict(payload_from_context(ctx))
    row = await first_table_record(GnapGrant, db, {"grant_id": payload["grant_id"]})
    if row is None:
        raise LookupError("GNAP grant not found")
    changes = {
        name: payload[name]
        for name in ("status", "subject_id", "expires_at", "access_request")
        if name in payload
    }
    return await update_table_record(GnapGrant, db, field_value(row, "id"), changes)


def _reject_raw_continuation(payload: Mapping[str, Any]) -> None:
    forbidden = {"continuation_token", "token"}.intersection(payload)
    if forbidden:
        raise ValueError("raw GNAP continuation tokens must not be persisted")


async def record_gnap_continuation(ctx: Mapping[str, Any]) -> Any:
    from tba_storage_gnap.tables import GnapContinuation

    payload = dict(payload_from_context(ctx))
    _reject_raw_continuation(payload)
    if not payload.get("token_digest"):
        raise ValueError("GNAP continuation requires token_digest")
    return await create_table_record(
        GnapContinuation, database_from_context(ctx), payload
    )


async def read_gnap_continuation(ctx: Mapping[str, Any]) -> Any:
    from tba_storage_gnap.tables import GnapContinuation

    payload = payload_from_context(ctx)
    _reject_raw_continuation(payload)
    return await first_table_record(
        GnapContinuation,
        database_from_context(ctx),
        {"token_digest": payload["token_digest"]},
    )


async def rotate_gnap_continuation(ctx: Mapping[str, Any]) -> Any:
    from tba_storage_gnap.tables import GnapContinuation

    db = database_from_context(ctx)
    payload = dict(payload_from_context(ctx))
    _reject_raw_continuation(payload)
    row = await first_table_record(
        GnapContinuation, db, {"continuation_id": payload["continuation_id"]}
    )
    if row is None:
        raise LookupError("GNAP continuation not found")
    return await update_table_record(
        GnapContinuation,
        db,
        field_value(row, "id"),
        {
            name: payload[name]
            for name in ("token_digest", "wait_seconds", "expires_at")
            if name in payload
        },
    )


async def record_gnap_interaction(ctx: Mapping[str, Any]) -> Any:
    from tba_storage_gnap.tables import GnapInteraction

    return await create_table_record(
        GnapInteraction, database_from_context(ctx), payload_from_context(ctx)
    )


async def complete_gnap_interaction(ctx: Mapping[str, Any]) -> Any:
    from tba_storage_gnap.tables import GnapInteraction

    db = database_from_context(ctx)
    payload = dict(payload_from_context(ctx))
    row = await first_table_record(
        GnapInteraction, db, {"interaction_id": payload["interaction_id"]}
    )
    if row is None:
        raise LookupError("GNAP interaction not found")
    return await update_table_record(
        GnapInteraction,
        db,
        field_value(row, "id"),
        {
            "status": payload.get("status", "complete"),
            "completed_at": payload.get("completed_at"),
        },
    )


__all__ = [
    "complete_gnap_interaction",
    "create_gnap_grant",
    "read_gnap_continuation",
    "read_gnap_grant",
    "record_gnap_client_instance",
    "record_gnap_continuation",
    "record_gnap_interaction",
    "rotate_gnap_continuation",
    "update_gnap_grant",
]
