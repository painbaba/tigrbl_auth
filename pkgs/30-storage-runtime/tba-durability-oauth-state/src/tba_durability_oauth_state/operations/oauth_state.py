"""Durable OAuth authorization, registration, and revocation operations."""

from __future__ import annotations

import datetime as dt
from collections.abc import Mapping
from datetime import timezone
from typing import Any

from tigrbl import (
    create_table_record,
    database_from_context,
    field_value,
    first_table_record,
    payload_from_context,
    update_table_record,
)


async def _registration_aggregate(db: Any, client_id: Any) -> dict[str, Any] | None:
    from tba_storage_oauth.tables import Client, ClientRegistration

    client = await first_table_record(Client, db, {"id": client_id})
    registration = await first_table_record(
        ClientRegistration,
        db,
        {"client_id": client_id},
    )
    if client is None or registration is None:
        return None
    return {"client": client, "registration": registration}


async def create_client_registration(ctx: Mapping[str, Any]) -> dict[str, Any]:
    """Create the canonical client and registration rows as one aggregate."""

    from tba_storage_oauth.tables import Client, ClientRegistration

    db = database_from_context(ctx)
    payload = dict(payload_from_context(ctx))
    client_id = payload["client_id"]
    if await _registration_aggregate(db, client_id) is not None:
        raise ValueError("client registration already exists")
    client = await create_table_record(
        Client,
        db,
        {
            "id": client_id,
            "tenant_id": payload["tenant_id"],
            "client_secret_hash": payload["client_secret_hash"],
            "redirect_uris": " ".join(payload["redirect_uris"]),
            "grant_types": " ".join(
                payload.get("grant_types") or ("authorization_code",)
            ),
            "response_types": " ".join(payload.get("response_types") or ("code",)),
        },
    )
    registration = await create_table_record(
        ClientRegistration,
        db,
        {
            "client_id": field_value(client, "id"),
            "tenant_id": payload["tenant_id"],
            "registration_metadata": dict(payload.get("metadata") or {}),
            "contacts": list(payload.get("contacts") or ()),
            "software_id": payload.get("software_id"),
            "software_version": payload.get("software_version"),
            "registration_access_token_hash": payload.get(
                "registration_access_token_hash"
            ),
            "registration_client_uri": payload.get("registration_client_uri"),
        },
    )
    return {"client": client, "registration": registration}


async def read_client_registration(ctx: Mapping[str, Any]) -> dict[str, Any] | None:
    """Read the canonical client-registration aggregate by client identifier."""

    payload = payload_from_context(ctx)
    return await _registration_aggregate(
        database_from_context(ctx),
        payload["client_id"],
    )


async def update_client_registration(ctx: Mapping[str, Any]) -> dict[str, Any]:
    """Replace mutable client and registration metadata without rotating secrets."""

    from tba_storage_oauth.tables import Client, ClientRegistration

    db = database_from_context(ctx)
    payload = dict(payload_from_context(ctx))
    aggregate = await _registration_aggregate(db, payload["client_id"])
    if aggregate is None:
        raise LookupError("client registration not found")
    client = aggregate["client"]
    registration = aggregate["registration"]
    client = await update_table_record(
        Client,
        db,
        field_value(client, "id"),
        {
            "redirect_uris": " ".join(payload["redirect_uris"]),
            "grant_types": " ".join(payload["grant_types"]),
            "response_types": " ".join(payload["response_types"]),
        },
    )
    registration = await update_table_record(
        ClientRegistration,
        db,
        field_value(registration, "id"),
        {
            "registration_metadata": dict(payload["metadata"]),
            "contacts": list(payload.get("contacts") or ()),
            "software_id": payload.get("software_id"),
            "software_version": payload.get("software_version"),
        },
    )
    return {"client": client, "registration": registration}


async def disable_client_registration(ctx: Mapping[str, Any]) -> dict[str, Any]:
    """Disable both sides of a client-registration aggregate without deleting history."""

    from tba_storage_oauth.tables import Client, ClientRegistration

    db = database_from_context(ctx)
    payload = payload_from_context(ctx)
    aggregate = await _registration_aggregate(db, payload["client_id"])
    if aggregate is None:
        raise LookupError("client registration not found")
    disabled_at = payload.get("disabled_at") or dt.datetime.now(timezone.utc)
    client = await update_table_record(
        Client,
        db,
        field_value(aggregate["client"], "id"),
        {"is_active": False},
    )
    registration = await update_table_record(
        ClientRegistration,
        db,
        field_value(aggregate["registration"], "id"),
        {"disabled_at": disabled_at},
    )
    return {"client": client, "registration": registration}


async def persist_authorization_code(ctx: Mapping[str, Any]) -> Any:
    """Persist an authorization code using the canonical create operation."""

    from tba_storage_oauth.tables import AuthCode

    return await create_table_record(
        AuthCode,
        database_from_context(ctx),
        payload_from_context(ctx),
    )


async def persist_pushed_authorization_request(ctx: Mapping[str, Any]) -> Any:
    """Persist one already-normalized pushed authorization request."""

    from tba_storage_oauth.tables import PushedAuthorizationRequest

    payload = dict(payload_from_context(ctx))
    if not payload.get("client_id"):
        raise ValueError("pushed authorization persistence requires client_id")
    params = payload.get("params")
    if not isinstance(params, Mapping):
        raise TypeError("pushed authorization params must be a mapping")
    payload["params"] = dict(params)
    return await create_table_record(
        PushedAuthorizationRequest,
        database_from_context(ctx),
        payload,
    )


async def upsert_client_registration(ctx: Mapping[str, Any]) -> Any:
    """Create or merge durable dynamic-client registration metadata."""

    from tba_storage_oauth.tables import ClientRegistration

    db = database_from_context(ctx)
    payload = dict(payload_from_context(ctx))
    client_id = payload["client_id"]
    row = await first_table_record(
        ClientRegistration,
        db,
        {"client_id": client_id},
    )
    merged = {
        "client_id": client_id,
        "tenant_id": payload.get("tenant_id") or field_value(row, "tenant_id"),
        "registration_metadata": payload.get("metadata")
        or payload.get("registration_metadata")
        or field_value(row, "registration_metadata"),
        "contacts": list(payload["contacts"])
        if payload.get("contacts") is not None
        else field_value(row, "contacts"),
        "software_id": payload.get("software_id") or field_value(row, "software_id"),
        "software_version": payload.get("software_version")
        or field_value(row, "software_version"),
        "registration_access_token_hash": payload.get("registration_access_token_hash")
        or field_value(row, "registration_access_token_hash"),
        "registration_client_uri": payload.get("registration_client_uri")
        or field_value(row, "registration_client_uri"),
        "issued_at": field_value(row, "issued_at") or dt.datetime.now(timezone.utc),
    }
    if row is None:
        return await create_table_record(ClientRegistration, db, merged)
    return await update_table_record(
        ClientRegistration,
        db,
        field_value(row, "id"),
        merged,
    )


async def record_revoked_token_hash(ctx: Mapping[str, Any]) -> Any:
    """Idempotently record a revoked token digest and its durable metadata."""

    from tba_storage_oauth.tables import RevokedToken

    db = database_from_context(ctx)
    payload = dict(payload_from_context(ctx))
    digest = payload["token_hash"]
    row = await first_table_record(RevokedToken, db, {"token_hash": digest})
    record = {
        "token_hash": digest,
        "token_type_hint": payload.get("token_type_hint")
        or field_value(row, "token_type_hint"),
        "refresh_family_id": payload.get("refresh_family_id")
        or field_value(row, "refresh_family_id"),
        "subject": payload.get("subject") or field_value(row, "subject"),
        "tenant_id": payload.get("tenant_id") or field_value(row, "tenant_id"),
        "client_id": payload.get("client_id") or field_value(row, "client_id"),
        "revoked_reason": payload.get("reason")
        or payload.get("revoked_reason")
        or field_value(row, "revoked_reason")
        or "revoked",
        "expires_at": payload.get("expires_at") or field_value(row, "expires_at"),
    }
    if row is None:
        return await create_table_record(RevokedToken, db, record)
    return await update_table_record(
        RevokedToken,
        db,
        field_value(row, "id"),
        record,
    )


async def is_token_hash_revoked(ctx: Mapping[str, Any]) -> bool:
    """Return whether a token digest exists in the revocation ledger."""

    from tba_storage_oauth.tables import RevokedToken

    payload = payload_from_context(ctx)
    return (
        await first_table_record(
            RevokedToken,
            database_from_context(ctx),
            {"token_hash": payload["token_hash"]},
        )
        is not None
    )


__all__ = [
    "create_client_registration",
    "disable_client_registration",
    "is_token_hash_revoked",
    "persist_authorization_code",
    "persist_pushed_authorization_request",
    "read_client_registration",
    "record_revoked_token_hash",
    "update_client_registration",
    "upsert_client_registration",
]
