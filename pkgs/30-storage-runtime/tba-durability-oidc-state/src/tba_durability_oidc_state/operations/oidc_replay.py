"""Durable OpenID Connect back-channel logout replay operation."""

from __future__ import annotations

import datetime as dt
import hashlib
from collections.abc import Mapping
from datetime import timezone
from typing import Any

from tigrbl import (
    create_table_record,
    database_from_context,
    delete_table_record,
    field_value,
    list_table_records,
)


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


def backchannel_logout_replay_key(*, issuer: str, client_id: str, jti: str) -> str:
    """Return the stable digest used by the logout replay ledger."""

    material = f"{issuer.strip()}\x1f{client_id.strip()}\x1f{jti.strip()}".encode()
    return hashlib.sha256(material).hexdigest()


async def register_backchannel_logout_replay(ctx: Mapping[str, Any]) -> Any:
    """Reject an active duplicate and persist a new logout-token observation."""

    from tba_storage_oidc.tables import BackchannelLogoutReplay

    payload = dict(ctx.get("payload") or {})
    db = database_from_context(ctx)
    jti = str(payload["jti"]).strip()
    issuer = str(payload["issuer"]).strip()
    client_id = str(payload["client_id"]).strip()
    now = _as_aware(payload.get("now") or dt.datetime.now(timezone.utc))
    expires_at = _as_aware(payload["expires_at"])
    key = backchannel_logout_replay_key(
        issuer=issuer,
        client_id=client_id,
        jti=jti,
    )

    rows = await list_table_records(BackchannelLogoutReplay, db=db)
    for row in rows:
        if _as_aware(field_value(row, "expires_at")) <= now:
            await delete_table_record(
                BackchannelLogoutReplay,
                db,
                field_value(row, "id"),
            )
            continue
        if field_value(row, "replay_key") == key:
            raise ValueError("replayed logout token")

    return await create_table_record(
        BackchannelLogoutReplay,
        db=db,
        payload={
            "replay_key": key,
            "jti": jti,
            "issuer": issuer,
            "client_id": client_id,
            "seen_at": now,
            "expires_at": expires_at,
        },
    )


__all__ = [
    "backchannel_logout_replay_key",
    "register_backchannel_logout_replay",
]
