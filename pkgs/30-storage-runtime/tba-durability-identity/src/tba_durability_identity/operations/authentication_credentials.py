"""Durable adapters used to compose authentication credential providers."""

from __future__ import annotations

from typing import Any

from tba_storage_authentication.tables import CredentialApiKey, CredentialServiceKey
from tba_storage_principals.tables import User

from tigrbl import list_table_records, maybe_await, read_table_record
from tba_durability_identity.operations.identities import (
    lookup_identity_by_identifier,
)


async def find_password_principals(db: Any, identifier: str) -> list[Any]:
    row = await lookup_identity_by_identifier(
        {"payload": {"identifier": identifier}, "db": db}
    )
    return [row] if row is not None else []


async def find_api_keys(db: Any, digest: str) -> list[Any]:
    return await list_table_records(CredentialApiKey, db, {"digest": digest})


async def find_service_keys(db: Any, digest: str) -> list[Any]:
    return await list_table_records(CredentialServiceKey, db, {"digest": digest})


async def resolve_user_principal(db: Any, key_row: Any) -> Any | None:
    user = getattr(key_row, "user", None) or getattr(key_row, "_user", None)
    if user is not None:
        return user
    principal_id = getattr(key_row, "principal_id", None)
    if principal_id in {None, ""}:
        return None
    try:
        return await read_table_record(User, db, principal_id)
    except Exception:
        return None


async def mark_credential_used(db: Any, key_row: Any) -> None:
    del db
    touch = getattr(key_row, "touch", None)
    if touch is not None:
        await maybe_await(touch())


__all__ = [
    "find_api_keys",
    "find_password_principals",
    "find_service_keys",
    "mark_credential_used",
    "resolve_user_principal",
]
