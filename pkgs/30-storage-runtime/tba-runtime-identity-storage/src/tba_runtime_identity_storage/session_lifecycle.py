"""Process-facing adapters over durable authentication-session operations."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from tigrbl_concrete.records import create_table_record, read_table_record
from .ops.sessions import (
    bind_session_client,
    get_active_session,
    rotate_session_cookie_secret,
    touch_session,
)
from .session import storage_session


async def create_session_async(
    *,
    user_id: UUID,
    tenant_id: UUID,
    username: str,
    client_id: UUID | None = None,
    expires_at: Any = None,
    cookie_secret_hash: str | None = None,
    session_state_salt: str | None = None,
):
    from tba_storage_oauth.tables import AuthSession

    async with storage_session() as db:
        return await create_table_record(
            AuthSession,
            db,
            {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "username": username,
                "client_id": client_id,
                "expires_at": expires_at,
                "cookie_secret_hash": cookie_secret_hash,
                "session_state_salt": session_state_salt,
            },
        )


async def get_session_async(session_id: UUID):
    from tba_storage_oauth.tables import AuthSession

    async with storage_session() as db:
        return await read_table_record(AuthSession, db, session_id)


async def get_active_session_async(session_id: UUID):
    async with storage_session() as db:
        return await get_active_session(
            {"payload": {"session_id": session_id}, "db": db}
        )


async def touch_session_async(session_id: UUID):
    async with storage_session() as db:
        return await touch_session({"payload": {"session_id": session_id}, "db": db})


async def rotate_session_cookie_secret_async(
    session_id: UUID, *, cookie_secret_hash: str
):
    async with storage_session() as db:
        return await rotate_session_cookie_secret(
            {
                "payload": {
                    "session_id": session_id,
                    "cookie_secret_hash": cookie_secret_hash,
                },
                "db": db,
            }
        )


async def bind_session_client_async(session_id: UUID, *, client_id: UUID | None):
    async with storage_session() as db:
        return await bind_session_client(
            {
                "payload": {"session_id": session_id, "client_id": client_id},
                "db": db,
            }
        )


__all__ = [
    "bind_session_client_async",
    "create_session_async",
    "get_active_session_async",
    "get_session_async",
    "rotate_session_cookie_secret_async",
    "touch_session_async",
]
