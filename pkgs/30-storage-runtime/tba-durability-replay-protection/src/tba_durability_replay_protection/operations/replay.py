"""Atomic durable replay reservation operation."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import IntegrityError

from tba_contracts_identity.replay import (
    ReplayReservationRequest,
    ReplayReservationResult,
    ReplayStoreDescriptor,
)
from tba_storage_replay_protection.tables import ReplayReservation
from tba_bases_replay import ReplayReservationBase

from tigrbl import database_from_context, maybe_await


DURABLE_REPLAY_DESCRIPTOR = ReplayStoreDescriptor(
    provider_id="replay:sql",
    persistence="durable",
    atomic_reservation=True,
    namespaces=("*",),
    tenant_isolation="key-scoped optional tenant identifier",
    expiry="required timezone-aware expires_at",
    retention="until expires_at plus operator purge interval",
    purge="expired rows are replaceable; scheduled purge is operator-owned",
    audit="reservation outcome exposes provider and digest",
    availability="database transaction and unique-constraint availability",
)


def _request(ctx: Mapping[str, Any]) -> ReplayReservationRequest:
    value = ctx.get("payload", ctx.get("request"))
    if not isinstance(value, ReplayReservationRequest):
        raise TypeError("replay operation payload must be ReplayReservationRequest")
    return value


async def check_and_reserve(ctx: Mapping[str, Any]) -> ReplayReservationResult:
    """Reserve a replay digest using the table's unique constraint."""

    request = _request(ctx)
    db = database_from_context(ctx)
    digest = ReplayReservationBase.digest_key(request.key)
    now = datetime.now(timezone.utc)
    rows = await maybe_await(
        ReplayReservation.handlers.list.core(
            ReplayReservation,
            filters={"key_digest": digest},
            db=db,
            limit=1,
        )
    )
    existing = next(iter(rows or ()), None)
    if existing is not None:
        expiry = getattr(existing, "expires_at", None)
        if expiry is None or expiry > now:
            return ReplayReservationResult(
                False,
                digest,
                expiry or request.expires_at,
                duplicate=True,
                provider_id=DURABLE_REPLAY_DESCRIPTOR.provider_id,
            )
        await maybe_await(
            ReplayReservation.handlers.delete.core(
                ReplayReservation, getattr(existing, "id"), db
            )
        )
    try:
        await maybe_await(
            ReplayReservation.handlers.create.core(
                ReplayReservation,
                {
                    "namespace": request.key.namespace,
                    "key_digest": digest,
                    "tenant_id": request.key.tenant_id,
                    "issuer": request.key.issuer,
                    "expires_at": request.expires_at,
                    "reservation_context": dict(request.context),
                },
                db,
            )
        )
    except IntegrityError:
        return ReplayReservationResult(
            False,
            digest,
            request.expires_at,
            duplicate=True,
            provider_id=DURABLE_REPLAY_DESCRIPTOR.provider_id,
        )
    return ReplayReservationResult(
        True,
        digest,
        request.expires_at,
        provider_id=DURABLE_REPLAY_DESCRIPTOR.provider_id,
    )


__all__ = ["DURABLE_REPLAY_DESCRIPTOR", "check_and_reserve"]
