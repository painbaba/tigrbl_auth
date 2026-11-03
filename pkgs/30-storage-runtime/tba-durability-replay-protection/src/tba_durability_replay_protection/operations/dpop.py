"""Table-backed DPoP replay and nonce operations."""

from __future__ import annotations

import datetime as dt
import secrets
from datetime import timezone
from typing import Any

from tba_storage_replay_protection.tables import DpopNonce, DpopReplay
from tba_storage_replay_protection.tables.dpop_nonce import nonce_hash, nonce_payload
from tba_storage_replay_protection.tables.dpop_replay import replay_payload
from tba_contracts_security_trust import DPoPNonceRecord, DPoPProofClaims

from tigrbl import (
    clear_records,
    create_record,
    delete_record,
    field,
    first_record,
    list_records,
    update_record,
)

DEFAULT_DPOP_TTL_SECONDS = 300


def _now() -> dt.datetime:
    return dt.datetime.now(timezone.utc)


def _as_aware(value: Any) -> dt.datetime:
    if isinstance(value, dt.datetime):
        parsed = value
    elif isinstance(value, (int, float)):
        parsed = dt.datetime.fromtimestamp(value, tz=timezone.utc)
    else:
        parsed = dt.datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


async def purge_expired_dpop_replays(
    db: Any, *, now: dt.datetime | None = None
) -> None:
    current = _as_aware(now or _now())
    for row in await list_records(DpopReplay, db):
        expires_at = _as_aware(field(row, "expires_at"))
        if expires_at <= current:
            await delete_record(DpopReplay, db, field(row, "id"))


async def check_and_store_dpop_replay(
    db: Any,
    claims: DPoPProofClaims,
    *,
    ttl_s: int = DEFAULT_DPOP_TTL_SECONDS,
) -> bool:
    proof_iat = _as_aware(claims.iat if claims.iat is not None else _now())
    await purge_expired_dpop_replays(db, now=_now())
    payload = replay_payload(
        jkt=claims.jkt,
        jti=claims.jti,
        htm=claims.htm,
        htu=claims.htu,
        ath=claims.ath,
        proof_iat=proof_iat,
        first_seen_at=_now(),
        expires_at=proof_iat + dt.timedelta(seconds=max(int(ttl_s), 1)),
    )
    existing = await first_record(DpopReplay, db, {"replay_key": payload["replay_key"]})
    if existing is not None:
        return True
    await create_record(DpopReplay, db, payload)
    return False


async def dpop_replay_snapshot(db: Any) -> dict[str, int]:
    current = _now()
    await purge_expired_dpop_replays(db, now=current)
    return {
        str(field(row, "replay_key")): int(
            _as_aware(field(row, "expires_at")).timestamp()
        )
        for row in await list_records(DpopReplay, db)
    }


async def clear_dpop_replays(db: Any) -> None:
    await clear_records(DpopReplay, db)


async def purge_expired_dpop_nonces(db: Any, *, now: dt.datetime | None = None) -> None:
    current = _as_aware(now or _now())
    for row in await list_records(DpopNonce, db):
        expires_at = _as_aware(field(row, "expires_at"))
        if expires_at <= current:
            await delete_record(DpopNonce, db, field(row, "id"))


async def issue_dpop_nonce(
    db: Any,
    *,
    ttl_s: int = DEFAULT_DPOP_TTL_SECONDS,
    client_id: str | None = None,
    authorization_server_id: str | None = None,
    resource_server_id: str | None = None,
    jkt: str | None = None,
) -> str:
    nonce = secrets.token_urlsafe(24)
    await register_dpop_nonce(
        db,
        nonce,
        ttl_s=ttl_s,
        client_id=client_id,
        authorization_server_id=authorization_server_id,
        resource_server_id=resource_server_id,
        jkt=jkt,
    )
    return nonce


async def register_dpop_nonce(
    db: Any,
    nonce: str,
    *,
    ttl_s: int = DEFAULT_DPOP_TTL_SECONDS,
    client_id: str | None = None,
    authorization_server_id: str | None = None,
    resource_server_id: str | None = None,
    jkt: str | None = None,
) -> str:
    now = _now()
    await purge_expired_dpop_nonces(db, now=now)
    payload = nonce_payload(
        nonce=str(nonce),
        issued_at=now,
        expires_at=now + dt.timedelta(seconds=max(int(ttl_s), 1)),
        client_id=client_id,
        authorization_server_id=authorization_server_id,
        resource_server_id=resource_server_id,
        jkt=jkt,
    )
    existing = await first_record(DpopNonce, db, {"nonce_hash": payload["nonce_hash"]})
    if existing is not None:
        await update_record(DpopNonce, db, field(existing, "id"), payload)
    else:
        await create_record(DpopNonce, db, payload)
    return str(nonce)


async def consume_dpop_nonce(db: Any, nonce: str, *, now: int | None = None) -> bool:
    current = _as_aware(now if now is not None else _now())
    await purge_expired_dpop_nonces(db, now=current)
    row = await first_record(DpopNonce, db, {"nonce_hash": nonce_hash(str(nonce))})
    if row is None:
        return False
    expires_at = _as_aware(field(row, "expires_at"))
    if field(row, "consumed_at") is not None or expires_at <= current:
        return False
    await update_record(DpopNonce, db, field(row, "id"), {"consumed_at": current})
    return True


async def dpop_nonce_snapshot(db: Any) -> dict[str, DPoPNonceRecord]:
    current = _now()
    await purge_expired_dpop_nonces(db, now=current)
    return {
        str(field(row, "nonce_hash")): DPoPNonceRecord(
            nonce=str(field(row, "nonce_hash")),
            expires_at=int(_as_aware(field(row, "expires_at")).timestamp()),
        )
        for row in await list_records(DpopNonce, db)
        if field(row, "consumed_at") is None
    }


async def clear_dpop_nonces(db: Any) -> None:
    await clear_records(DpopNonce, db)


__all__ = [
    "DEFAULT_DPOP_TTL_SECONDS",
    "check_and_store_dpop_replay",
    "clear_dpop_nonces",
    "clear_dpop_replays",
    "consume_dpop_nonce",
    "dpop_nonce_snapshot",
    "dpop_replay_snapshot",
    "issue_dpop_nonce",
    "purge_expired_dpop_nonces",
    "purge_expired_dpop_replays",
    "register_dpop_nonce",
]
