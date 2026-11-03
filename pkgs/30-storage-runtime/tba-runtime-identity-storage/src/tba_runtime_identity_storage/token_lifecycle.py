"""Process-facing adapters over carrier-neutral durable token operations."""

from __future__ import annotations

from datetime import timezone
from typing import Any

from tba_primitives_identity.clock import utc_now
from tba_primitives_identity.digests import token_hash
from .sync import run_async
from tigrbl_concrete.records import (
    delete_table_record,
    field_value,
    first_table_record,
    list_table_records,
    update_table_record,
)
from .ops.oauth_state import is_token_hash_revoked, record_revoked_token_hash
from .ops.tokens import introspect_token_record
from .session import storage_session
from .token_persistence import remove_token_record_async, upsert_token_record_async


async def introspect_token_async(token: str) -> dict[str, Any]:
    digest = token_hash(token)
    try:
        async with storage_session() as db:
            if await is_token_hash_revoked(
                {"payload": {"token_hash": digest}, "db": db}
            ):
                return {"active": False}
            return await introspect_token_record(
                {"payload": {"token_hash": digest}, "db": db}
            )
    except Exception:
        return {"active": False}


async def revoke_token_async(
    token: str,
    token_type_hint: str | None = None,
    reason: str | None = None,
) -> str:
    from tba_storage_token.tables import TokenRecord

    digest = token_hash(token)
    now = utc_now()
    async with storage_session() as db:
        row = await first_table_record(TokenRecord, db, {"token_hash": digest})
        payload: dict[str, Any] = {
            "token_hash": digest,
            "token_type_hint": token_type_hint,
            "reason": reason or "revoked",
        }
        if row is not None:
            await update_table_record(
                TokenRecord,
                db,
                field_value(row, "id"),
                {
                    "active": False,
                    "token_status": "revoked",
                    "revoked_at": now,
                    "revoked_reason": reason or "revoked",
                },
            )
            payload.update(
                subject=field_value(row, "subject"),
                tenant_id=field_value(row, "tenant_id"),
                client_id=field_value(row, "client_id"),
                expires_at=field_value(row, "expires_at"),
                token_type_hint=token_type_hint or field_value(row, "token_type_hint"),
            )
        await record_revoked_token_hash({"payload": payload, "db": db})
    return digest


async def is_token_revoked_async(token: str) -> bool:
    from tba_storage_token.tables import TokenRecord

    digest = token_hash(token)
    async with storage_session() as db:
        if await is_token_hash_revoked({"payload": {"token_hash": digest}, "db": db}):
            return True
        row = await first_table_record(TokenRecord, db, {"token_hash": digest})
        if row is None:
            return False
        if field_value(row, "revoked_at") is not None:
            return True
        expires_at = field_value(row, "expires_at")
        if expires_at is not None:
            expiry = (
                expires_at
                if expires_at.tzinfo is not None
                else expires_at.replace(tzinfo=timezone.utc)
            )
            if expiry <= utc_now():
                return True
        return not bool(field_value(row, "active"))


async def reset_token_state_async() -> None:
    from tba_storage_oauth.tables import RevokedToken
    from tba_storage_token.tables import TokenRecord

    try:
        async with storage_session() as db:
            for table in (RevokedToken, TokenRecord):
                for row in await list_table_records(table, db):
                    await delete_table_record(table, db, field_value(row, "id"))
    except Exception:
        # An optional or not-yet-migrated durable store has no state to clear.
        return None


def upsert_token_record(*args: Any, **kwargs: Any) -> str:
    return run_async(upsert_token_record_async(*args, **kwargs))


def remove_token_record(token: str) -> None:
    return run_async(remove_token_record_async(token))


def introspect_token(token: str) -> dict[str, Any]:
    return run_async(introspect_token_async(token))


def revoke_token(*args: Any, **kwargs: Any) -> str:
    return run_async(revoke_token_async(*args, **kwargs))


def is_token_revoked(token: str) -> bool:
    return bool(run_async(is_token_revoked_async(token)))


def reset_token_state() -> None:
    run_async(reset_token_state_async())


is_revoked = is_token_revoked
is_revoked_async = is_token_revoked_async
reset_revocations = reset_token_state
reset_revocations_async = reset_token_state_async

__all__ = [
    "introspect_token",
    "introspect_token_async",
    "is_revoked",
    "is_revoked_async",
    "is_token_revoked",
    "is_token_revoked_async",
    "remove_token_record",
    "remove_token_record_async",
    "reset_revocations",
    "reset_revocations_async",
    "reset_token_state",
    "reset_token_state_async",
    "revoke_token",
    "revoke_token_async",
    "upsert_token_record",
    "upsert_token_record_async",
]
