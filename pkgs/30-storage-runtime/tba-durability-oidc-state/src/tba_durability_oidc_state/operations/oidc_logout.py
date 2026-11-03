"""Durable OpenID Connect logout-propagation operations."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tba_primitives_identity.clock import utc_now

from tigrbl import (
    create_table_record,
    database_from_context,
    field_value,
    list_table_records,
    payload_from_context,
    read_table_record,
    update_table_record,
)


def _latest(rows: list[Any]) -> Any:
    if not rows:
        return None
    return sorted(
        rows,
        key=lambda item: str(
            field_value(item, "created_at", "") or field_value(item, "id", "")
        ),
        reverse=True,
    )[0]


def _logout_id(ctx: Mapping[str, Any]) -> Any:
    payload = payload_from_context(ctx)
    path = ctx.get("path_params") or {}
    return payload.get("logout_id") or payload.get("id") or path.get("id")


async def latest_logout_for_session(ctx: Mapping[str, Any]) -> Any:
    from tba_storage_oidc.tables import LogoutState

    payload = payload_from_context(ctx)
    path = ctx.get("path_params") or {}
    session_id = payload.get("session_id") or path.get("session_id")
    return _latest(
        await list_table_records(
            LogoutState,
            database_from_context(ctx),
            {"session_id": session_id},
        )
    )


async def update_logout_metadata(ctx: Mapping[str, Any]) -> Any:
    from tba_storage_oidc.tables import LogoutState

    db = database_from_context(ctx)
    payload = dict(payload_from_context(ctx))
    logout_id = _logout_id(ctx)
    row = await read_table_record(LogoutState, db, logout_id)
    if row is None:
        return None
    current = dict(field_value(row, "logout_metadata") or {})
    if payload.get("metadata"):
        current.update(dict(payload["metadata"]))
    update: dict[str, Any] = {"logout_metadata": current or None}
    if payload.get("status") is not None:
        update["status"] = payload["status"]
    return await update_table_record(LogoutState, db, logout_id, update)


async def mark_logout_channel(ctx: Mapping[str, Any]) -> Any:
    from tba_storage_oidc.tables import LogoutState

    db = database_from_context(ctx)
    payload = dict(payload_from_context(ctx))
    logout_id = _logout_id(ctx)
    row = await read_table_record(LogoutState, db, logout_id)
    if row is None:
        return None
    channel = str(payload["channel"])
    status = str(payload.get("status") or "complete")
    now = utc_now()
    now_iso = now.replace(microsecond=0).isoformat()
    current_meta = dict(field_value(row, "logout_metadata") or {})
    channel_meta = dict(current_meta.get(channel) or {})
    if payload.get("metadata"):
        channel_meta.update(dict(payload["metadata"]))
    delivery = dict(channel_meta.get("delivery") or {})
    delivery.update(
        {
            "channel": channel,
            "status": status,
            "attempts": max(int(delivery.get("attempts", 0) or 0) + 1, 1),
            "updated_at": now_iso,
        }
    )
    if payload.get("reason") is not None:
        delivery["reason"] = str(payload["reason"])
    if payload.get("retry_after_seconds") is not None:
        delivery["retry_after_seconds"] = int(payload["retry_after_seconds"])
    if status == "complete":
        delivery["completed_at"] = now_iso
    channel_meta["delivery"] = delivery
    channel_meta["status"] = delivery["status"]
    current_meta[channel] = channel_meta
    current_meta[f"{channel}_delivery"] = dict(delivery)

    update: dict[str, Any] = {"logout_metadata": current_meta or None}
    if channel == "frontchannel" and status == "complete":
        update["frontchannel_completed_at"] = now
    elif channel == "backchannel" and status == "complete":
        update["backchannel_completed_at"] = now
    front_done = update.get(
        "frontchannel_completed_at",
        field_value(row, "frontchannel_completed_at"),
    )
    back_done = update.get(
        "backchannel_completed_at",
        field_value(row, "backchannel_completed_at"),
    )
    if (not field_value(row, "frontchannel_required") or front_done is not None) and (
        not field_value(row, "backchannel_required") or back_done is not None
    ):
        update["status"] = "complete"
        update["propagated_at"] = now
    else:
        update["status"] = (
            "pending" if status != "complete" else field_value(row, "status")
        )
    return await update_table_record(LogoutState, db, logout_id, update)


async def ensure_logout_for_session(ctx: Mapping[str, Any]) -> Any:
    from tba_storage_oidc.tables import LogoutState

    payload = dict(payload_from_context(ctx))
    session_id = payload["session_id"]
    db = database_from_context(ctx)
    latest = _latest(
        await list_table_records(LogoutState, db, {"session_id": session_id})
    )
    if latest is not None:
        current_meta = dict(field_value(latest, "logout_metadata") or {})
        if payload.get("metadata"):
            current_meta.update(dict(payload["metadata"]))
        return await update_table_record(
            LogoutState,
            db,
            field_value(latest, "id"),
            {
                "logout_metadata": current_meta or None,
                "frontchannel_required": bool(
                    field_value(latest, "frontchannel_required")
                    or payload.get("frontchannel_required")
                ),
                "backchannel_required": bool(
                    field_value(latest, "backchannel_required")
                    or payload.get("backchannel_required")
                ),
            },
        )
    return await create_table_record(
        LogoutState,
        db,
        {
            "session_id": session_id,
            "initiated_by": payload.get("initiated_by") or "rp_logout",
            "reason": payload.get("reason") or "logout",
            "frontchannel_required": bool(payload.get("frontchannel_required")),
            "backchannel_required": bool(payload.get("backchannel_required")),
            "logout_metadata": payload.get("metadata"),
            "status": "pending",
        },
    )


__all__ = [
    "ensure_logout_for_session",
    "latest_logout_for_session",
    "mark_logout_channel",
    "update_logout_metadata",
]
