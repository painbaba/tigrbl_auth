"""Crypto-key persistence lifecycle hooks."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tigrbl import Hook, HookPhase
from tba_contracts_security_trust import (
    normalize_key_usages,
    resolve_key_allowed_operations,
)

from tigrbl import (
    create_table_record,
    database_from_context,
    field_value,
    list_table_records,
    record_identifier,
)


def normalize_key_usage_values(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Materialize canonical usage and allowed-operation storage values."""

    cleaned = dict(payload)
    key_kind = cleaned.get("key_kind", "asymmetric")
    usages = normalize_key_usages(cleaned.get("key_usages"))
    operations = resolve_key_allowed_operations(
        kind=key_kind,
        usages=usages,
        allowed_ops=(cleaned.get("allowed_ops") if "allowed_ops" in cleaned else None),
    )
    cleaned.update(
        {
            "key_kind": str(getattr(key_kind, "value", key_kind)),
            "key_usages": [usage.value for usage in usages],
            "allowed_ops": [operation.value for operation in operations],
        }
    )
    return cleaned


async def normalize_key_usage_policy(ctx: Mapping[str, Any]) -> None:
    payload = ctx.get("payload")
    if isinstance(payload, Mapping) and isinstance(ctx, dict):
        ctx["payload"] = normalize_key_usage_values(payload)


async def seed_primary_key_version(ctx: Mapping[str, Any]) -> None:
    from tba_storage_key_material.tables import CryptoKeyVersion

    db = database_from_context(ctx)
    row = ctx.get("result") or ctx.get("object") or ctx.get("item")
    if row is None:
        return
    key_id = record_identifier(row)
    version = int(field_value(row, "primary_version", 1) or 1)
    existing = await list_table_records(
        CryptoKeyVersion,
        db,
        {"key_id": key_id, "version": version},
    )
    if existing:
        return
    await create_table_record(
        CryptoKeyVersion,
        db,
        {
            "key_id": key_id,
            "version": version,
            "status": "active",
            "public_material": field_value(row, "public_material"),
            "public_material_format": field_value(row, "public_material_format"),
            "provider_key_ref": field_value(row, "provider_key_ref"),
            "provider": field_value(row, "provider"),
            "allowed_ops": field_value(row, "allowed_ops"),
            "fingerprint": field_value(row, "fingerprint"),
        },
    )


async def ensure_key_enabled(ctx: Mapping[str, Any]) -> None:
    from tba_storage_key_material.tables import CryptoKey

    payload = ctx.get("payload") or {}
    kid = payload.get("kid") if isinstance(payload, Mapping) else None
    if not kid:
        return
    rows = await list_table_records(
        CryptoKey,
        database_from_context(ctx),
        {"kid": str(kid)},
    )
    row = rows[0] if rows else None
    if row is None or field_value(row, "status") != "active":
        raise LookupError("active crypto key not found")
    if isinstance(ctx, dict):
        ctx["crypto_key"] = row


CRYPTO_KEY_RUNTIME_HOOKS = (
    Hook(
        phase=HookPhase.PRE_HANDLER,
        fn=normalize_key_usage_policy,
        ops=("create", "update"),
        name="normalize_key_usage_policy",
    ),
    Hook(
        phase=HookPhase.POST_HANDLER,
        fn=seed_primary_key_version,
        ops="create",
        name="seed_primary_key_version",
    ),
    Hook(
        phase=HookPhase.PRE_HANDLER,
        fn=ensure_key_enabled,
        ops="rotate_record",
        name="ensure_key_enabled",
    ),
)


__all__ = [
    "CRYPTO_KEY_RUNTIME_HOOKS",
    "ensure_key_enabled",
    "normalize_key_usage_policy",
    "normalize_key_usage_values",
    "seed_primary_key_version",
]
