"""Process-facing adapters over durable consent operations."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from .sync import run_async
from tigrbl_concrete.records import create_table_record
from .ops.consents import revoke_consent_for_user
from .session import storage_session


async def record_consent_async(
    *,
    user_id: UUID,
    tenant_id: UUID,
    client_id: UUID,
    scope: str,
    claims: dict[str, Any] | None = None,
    expires_at: datetime | None = None,
):
    """Persist an active consent through the canonical table operation."""

    from tba_storage_consent.tables import Consent

    async with storage_session() as db:
        return await create_table_record(
            Consent,
            db,
            {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "client_id": client_id,
                "scope": scope,
                "claims": claims,
                "expires_at": expires_at,
                "state": "active",
            },
        )


async def revoke_consent_async(consent_id: UUID):
    """Revoke one consent using the caller-independent durable adapter."""

    async with storage_session() as db:
        return await revoke_consent_for_user(
            {
                "path_params": {"id": consent_id},
                "payload": {"id": consent_id},
                "db": db,
            }
        )


def record_consent(**kwargs: Any):
    return run_async(record_consent_async(**kwargs))


def revoke_consent(consent_id: UUID):
    return run_async(revoke_consent_async(consent_id))


__all__ = [
    "record_consent",
    "record_consent_async",
    "revoke_consent",
    "revoke_consent_async",
]
