"""Process-facing adapters over durable client-registration operations."""

from __future__ import annotations

from typing import Any

from .sync import run_async
from tigrbl_concrete.records import first_table_record
from .ops.oauth_state import upsert_client_registration as _upsert_registration
from .session import storage_session


async def get_client_registration_async(client_id: Any):
    from tba_storage_oauth.tables import ClientRegistration

    async with storage_session() as db:
        return await first_table_record(
            ClientRegistration,
            db,
            {"client_id": client_id},
        )


async def upsert_client_registration_async(**kwargs: Any):
    async with storage_session() as db:
        return await _upsert_registration({"payload": kwargs, "db": db})


def get_client_registration(client_id: Any):
    return run_async(get_client_registration_async(client_id))


def upsert_client_registration(**kwargs: Any):
    return run_async(upsert_client_registration_async(**kwargs))


__all__ = [
    "get_client_registration",
    "get_client_registration_async",
    "upsert_client_registration",
    "upsert_client_registration_async",
]
