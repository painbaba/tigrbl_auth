"""Executable table specifications for durable DPoP state."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tba_storage_replay_protection.tables import DpopNonce, DpopReplay
from tba_contracts_security_trust import DPoPProofClaims

from tigrbl import deriveTableSpec
from tigrbl import makeOp
from tigrbl import database_from_context
from tba_durability_replay_protection.operations.dpop import (
    check_and_store_dpop_replay,
    clear_dpop_nonces,
    clear_dpop_replays,
    consume_dpop_nonce,
    dpop_nonce_snapshot,
    dpop_replay_snapshot,
    issue_dpop_nonce,
    purge_expired_dpop_nonces,
    purge_expired_dpop_replays,
    register_dpop_nonce,
)


def _payload(ctx: Mapping[str, Any]) -> Mapping[str, Any]:
    value = ctx.get("payload", {})
    if not isinstance(value, Mapping):
        raise TypeError("DPoP runtime operation payload must be a mapping")
    return value


async def _check_and_store(ctx: Mapping[str, Any]) -> bool:
    payload = _payload(ctx)
    claims = payload.get("claims")
    if not isinstance(claims, DPoPProofClaims):
        raise TypeError("DPoP replay operation requires DPoPProofClaims")
    return await check_and_store_dpop_replay(
        database_from_context(ctx),
        claims,
        ttl_s=int(payload.get("ttl_s", 300)),
    )


async def _issue_nonce(ctx: Mapping[str, Any]) -> str:
    return await issue_dpop_nonce(database_from_context(ctx), **dict(_payload(ctx)))


async def _register_nonce(ctx: Mapping[str, Any]) -> str:
    payload = dict(_payload(ctx))
    try:
        nonce = str(payload.pop("nonce"))
    except KeyError as exc:
        raise ValueError("DPoP nonce registration requires nonce") from exc
    return await register_dpop_nonce(database_from_context(ctx), nonce, **payload)


async def _consume_nonce(ctx: Mapping[str, Any]) -> bool:
    payload = _payload(ctx)
    try:
        nonce = str(payload["nonce"])
    except KeyError as exc:
        raise ValueError("DPoP nonce consumption requires nonce") from exc
    return await consume_dpop_nonce(
        database_from_context(ctx), nonce, now=payload.get("now")
    )


async def _replay_snapshot(ctx: Mapping[str, Any]) -> dict[str, int]:
    return await dpop_replay_snapshot(database_from_context(ctx))


async def _nonce_snapshot(ctx: Mapping[str, Any]) -> dict[str, Any]:
    return await dpop_nonce_snapshot(database_from_context(ctx))


async def _purge_replays(ctx: Mapping[str, Any]) -> None:
    await purge_expired_dpop_replays(
        database_from_context(ctx), now=_payload(ctx).get("now")
    )


async def _purge_nonces(ctx: Mapping[str, Any]) -> None:
    await purge_expired_dpop_nonces(
        database_from_context(ctx), now=_payload(ctx).get("now")
    )


async def _clear_replays(ctx: Mapping[str, Any]) -> None:
    await clear_dpop_replays(database_from_context(ctx))


async def _clear_nonces(ctx: Mapping[str, Any]) -> None:
    await clear_dpop_nonces(database_from_context(ctx))


def makeDpopReplayRuntimeSpec(table: type = DpopReplay) -> type:
    return deriveTableSpec(
        table,
        ops=(
            makeOp(
                extra={"owner_layer": "30-storage-runtime"},
                expose_routes=False,
                expose_rpc=False,
                expose_method=True,
                tx_scope="read_write",
                alias="check_and_store",
                handler=_check_and_store,
            ),
            makeOp(
                extra={"owner_layer": "30-storage-runtime"},
                expose_routes=False,
                expose_rpc=False,
                expose_method=True,
                tx_scope="read_write",
                alias="snapshot",
                handler=_replay_snapshot,
            ),
            makeOp(
                extra={"owner_layer": "30-storage-runtime"},
                expose_routes=False,
                expose_rpc=False,
                expose_method=True,
                tx_scope="read_write",
                alias="purge_expired",
                handler=_purge_replays,
            ),
            makeOp(
                extra={"owner_layer": "30-storage-runtime"},
                expose_routes=False,
                expose_rpc=False,
                expose_method=True,
                tx_scope="read_write",
                alias="clear",
                handler=_clear_replays,
            ),
        ),
    )


def makeDpopNonceRuntimeSpec(table: type = DpopNonce) -> type:
    return deriveTableSpec(
        table,
        ops=(
            makeOp(
                extra={"owner_layer": "30-storage-runtime"},
                expose_routes=False,
                expose_rpc=False,
                expose_method=True,
                tx_scope="read_write",
                alias="issue",
                handler=_issue_nonce,
            ),
            makeOp(
                extra={"owner_layer": "30-storage-runtime"},
                expose_routes=False,
                expose_rpc=False,
                expose_method=True,
                tx_scope="read_write",
                alias="register",
                handler=_register_nonce,
            ),
            makeOp(
                extra={"owner_layer": "30-storage-runtime"},
                expose_routes=False,
                expose_rpc=False,
                expose_method=True,
                tx_scope="read_write",
                alias="consume",
                handler=_consume_nonce,
            ),
            makeOp(
                extra={"owner_layer": "30-storage-runtime"},
                expose_routes=False,
                expose_rpc=False,
                expose_method=True,
                tx_scope="read_write",
                alias="snapshot",
                handler=_nonce_snapshot,
            ),
            makeOp(
                extra={"owner_layer": "30-storage-runtime"},
                expose_routes=False,
                expose_rpc=False,
                expose_method=True,
                tx_scope="read_write",
                alias="purge_expired",
                handler=_purge_nonces,
            ),
            makeOp(
                extra={"owner_layer": "30-storage-runtime"},
                expose_routes=False,
                expose_rpc=False,
                expose_method=True,
                tx_scope="read_write",
                alias="clear",
                handler=_clear_nonces,
            ),
        ),
    )


DpopReplayTable = DpopReplay
DpopNonceTable = DpopNonce
DpopReplayRuntimeSpec = makeDpopReplayRuntimeSpec()
DpopNonceRuntimeSpec = makeDpopNonceRuntimeSpec()


__all__ = [
    "DpopNonceRuntimeSpec",
    "DpopNonceTable",
    "DpopReplayRuntimeSpec",
    "DpopReplayTable",
    "makeDpopNonceRuntimeSpec",
    "makeDpopReplayRuntimeSpec",
]
