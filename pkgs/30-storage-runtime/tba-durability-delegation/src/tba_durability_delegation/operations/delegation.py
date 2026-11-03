"""Durable delegation-grant lifecycle operations."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tba_primitives_identity.clock import utc_now

from tigrbl import (
    create_table_record,
    database_from_context,
    field_value,
    list_table_records,
    payload_from_context,
    read_table_record,
    record_identifier,
    update_table_record,
)


TERMINAL_GRANT_STATUSES = frozenset({"revoked", "expired", "replaced"})


async def _create_grant(db: Any, payload: Mapping[str, Any]) -> Any:
    from tba_storage_delegation.tables import DelegationGrant

    values = dict(payload)
    values.setdefault("status", "active")
    values.setdefault("effective_at", utc_now())
    return await create_table_record(DelegationGrant, db, values)


async def create_grant(ctx: Mapping[str, Any]) -> Any:
    return await _create_grant(database_from_context(ctx), payload_from_context(ctx))


async def inspect_grant(ctx: Mapping[str, Any]) -> Any:
    from tba_storage_delegation.tables import DelegationGrant

    payload = payload_from_context(ctx)
    return await read_table_record(
        DelegationGrant,
        database_from_context(ctx),
        payload["grant_id"],
    )


async def list_grants(ctx: Mapping[str, Any]) -> list[Any]:
    from tba_storage_delegation.tables import DelegationGrant

    filters = {
        key: value
        for key, value in dict(payload_from_context(ctx)).items()
        if value is not None
    }
    return await list_table_records(
        DelegationGrant, database_from_context(ctx), filters
    )


async def _transition_grant(
    ctx: Mapping[str, Any],
    *,
    status: str,
    timestamp_field: str,
) -> Any:
    from tba_storage_delegation.tables import DelegationGrant

    payload = payload_from_context(ctx)
    db = database_from_context(ctx)
    row = await read_table_record(DelegationGrant, db, payload["grant_id"])
    if row is None:
        return None
    return await update_table_record(
        DelegationGrant,
        db,
        record_identifier(row),
        {
            "status": status,
            timestamp_field: payload.get(timestamp_field) or utc_now(),
        },
    )


async def activate_grant(ctx: Mapping[str, Any]) -> Any:
    return await _transition_grant(
        ctx,
        status="active",
        timestamp_field="effective_at",
    )


async def expire_grant(ctx: Mapping[str, Any]) -> Any:
    return await _transition_grant(
        ctx,
        status="expired",
        timestamp_field="expires_at",
    )


async def replace_grant(ctx: Mapping[str, Any]) -> Any:
    from tba_storage_delegation.tables import DelegationGrant

    values = dict(payload_from_context(ctx))
    db = database_from_context(ctx)
    current = await read_table_record(DelegationGrant, db, values.pop("grant_id"))
    if current is None:
        return None
    current_id = record_identifier(current)
    replacement = await _create_grant(
        db,
        {
            "tenant_id": field_value(current, "tenant_id"),
            "realm": field_value(current, "realm", ""),
            "delegator_subject": field_value(current, "delegator_subject"),
            "delegate_subject": field_value(current, "delegate_subject"),
            "delegate_type": field_value(current, "delegate_type", "subject"),
            "parent_grant_id": current_id,
            "source_authority_ref": field_value(current, "source_authority_ref"),
            "policy_version": field_value(current, "policy_version"),
            "provenance_id": field_value(current, "provenance_id"),
            "constraints": field_value(current, "constraints"),
            "expires_at": field_value(current, "expires_at"),
            **values,
        },
    )
    await update_table_record(
        DelegationGrant,
        db,
        current_id,
        {
            "status": "replaced",
            "revoked_at": utc_now(),
            "revoked_reason": "replaced",
            "replaced_by_grant_id": record_identifier(replacement),
        },
    )
    return replacement


async def link_grant_edge(ctx: Mapping[str, Any]) -> Any:
    from tba_storage_delegation.tables import DelegationGrantEdge

    return await create_table_record(
        DelegationGrantEdge,
        database_from_context(ctx),
        {"active": True, **dict(payload_from_context(ctx))},
    )


async def _deactivate_children(db: Any, parent_grant_id: Any) -> list[Any]:
    from tba_storage_delegation.tables import DelegationGrantEdge

    children = await list_table_records(
        DelegationGrantEdge,
        db,
        {"parent_grant_id": parent_grant_id},
    )
    return [
        await update_table_record(
            DelegationGrantEdge,
            db,
            record_identifier(row),
            {"active": False},
        )
        for row in children
    ]


async def deactivate_grant_children(ctx: Mapping[str, Any]) -> list[Any]:
    return await _deactivate_children(
        database_from_context(ctx),
        payload_from_context(ctx)["parent_grant_id"],
    )


async def _revoke_one(
    db: Any,
    *,
    grant_id: Any,
    revoked_by: str | None,
    reason: str | None,
    collapse_descendants: bool,
) -> Any:
    from tba_storage_delegation.tables import DelegationGrant

    row = await read_table_record(DelegationGrant, db, grant_id)
    if row is None:
        return None
    row_id = record_identifier(row)
    revoked = await update_table_record(
        DelegationGrant,
        db,
        row_id,
        {
            "status": "revoked",
            "revoked_at": utc_now(),
            "revoked_by": revoked_by,
            "revoked_reason": reason,
        },
    )
    if collapse_descendants:
        children = await list_table_records(
            DelegationGrant,
            db,
            {"parent_grant_id": row_id},
        )
        for child in children:
            if str(field_value(child, "status")) not in TERMINAL_GRANT_STATUSES:
                await _revoke_one(
                    db,
                    grant_id=record_identifier(child),
                    revoked_by=revoked_by,
                    reason="ancestor-revoked",
                    collapse_descendants=True,
                )
        await _deactivate_children(db, row_id)
    return revoked


async def revoke_grant(ctx: Mapping[str, Any]) -> Any:
    payload = payload_from_context(ctx)
    return await _revoke_one(
        database_from_context(ctx),
        grant_id=payload["grant_id"],
        revoked_by=payload.get("revoked_by"),
        reason=payload.get("reason"),
        collapse_descendants=bool(payload.get("collapse_descendants")),
    )


async def persist_delegation_provenance(ctx: Mapping[str, Any]) -> Any:
    from tba_storage_delegation.tables import DelegationGrantProof

    return await create_table_record(
        DelegationGrantProof,
        database_from_context(ctx),
        payload_from_context(ctx),
    )


async def link_delegation_token(ctx: Mapping[str, Any]) -> Any:
    from tba_storage_delegation.tables import DelegationGrantTokenLink

    return await create_table_record(
        DelegationGrantTokenLink,
        database_from_context(ctx),
        payload_from_context(ctx),
    )


async def list_tokens_for_grant(ctx: Mapping[str, Any]) -> list[Any]:
    from tba_storage_delegation.tables import DelegationGrantTokenLink

    return await list_table_records(
        DelegationGrantTokenLink,
        database_from_context(ctx),
        {"grant_id": payload_from_context(ctx)["grant_id"]},
    )


__all__ = [
    "TERMINAL_GRANT_STATUSES",
    "activate_grant",
    "create_grant",
    "deactivate_grant_children",
    "expire_grant",
    "inspect_grant",
    "link_delegation_token",
    "link_grant_edge",
    "list_grants",
    "list_tokens_for_grant",
    "persist_delegation_provenance",
    "replace_grant",
    "revoke_grant",
]
