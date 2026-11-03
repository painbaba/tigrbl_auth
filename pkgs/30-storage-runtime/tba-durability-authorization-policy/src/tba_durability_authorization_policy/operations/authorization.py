"""Durable authorization membership and delegated-scope operations."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tba_storage_authorization_policy.tables import AttributePolicy, DelegatedAdminScope, PolicyCondition, Role, TenantMembership

from tigrbl import (
    create_table_record,
    clear_table_records,
    database_from_context,
    field_value,
    first_table_record,
    list_table_records,
    payload_from_context,
    record_identifier,
    update_table_record,
)


def _strings(values: Any) -> tuple[str, ...]:
    if values is None or values == "" or values is False:
        return ()
    if isinstance(values, str):
        return (values,)
    return tuple(sorted({str(value) for value in values if value not in {None, ""}}))


async def grant_membership(ctx: Mapping[str, Any]) -> object:
    values = dict(payload_from_context(ctx))
    db = database_from_context(ctx)
    tenant_id = str(values["tenant_id"])
    principal_id = str(values["principal_id"])
    payload = {
        "tenant_id": tenant_id,
        "principal_id": principal_id,
        "roles": list(_strings(values.get("roles", ()))),
        "status": str(values.get("status", "active")),
    }
    existing = await first_table_record(
        TenantMembership,
        db,
        {"tenant_id": tenant_id, "principal_id": principal_id},
    )
    if existing is None:
        return await create_table_record(TenantMembership, db, payload)
    return await update_table_record(
        TenantMembership, db, record_identifier(existing), payload
    )


async def assign_role(ctx: Mapping[str, Any]) -> object:
    values = dict(payload_from_context(ctx))
    db = database_from_context(ctx)
    filters = {
        "tenant_id": values["tenant_id"],
        "principal_id": values["principal_id"],
    }
    existing = await first_table_record(TenantMembership, db, filters)
    roles = set(_strings(field_value(existing, "roles", ()))) if existing else set()
    roles.add(str(values["role_name"]))
    return await grant_membership(
        {
            "db": db,
            "payload": {**filters, "roles": roles, "status": "active"},
        }
    )


async def role_names_for_principal(ctx: Mapping[str, Any]) -> tuple[str, ...]:
    values = dict(payload_from_context(ctx))
    filters = {"principal_id": values["principal_id"]}
    if values.get("tenant_id") is not None:
        filters["tenant_id"] = values["tenant_id"]
    rows = await list_table_records(
        TenantMembership, database_from_context(ctx), filters
    )
    roles: set[str] = set()
    for row in rows:
        if field_value(row, "status", "active") == "active":
            roles.update(_strings(field_value(row, "roles", ())))
    return tuple(sorted(roles))


async def upsert_role(ctx: Mapping[str, Any]) -> object:
    values = dict(payload_from_context(ctx))
    db = database_from_context(ctx)
    filters = {
        "name": str(values["name"]),
        "tenant_id": values.get("tenant_id"),
    }
    payload = {
        **filters,
        "permissions": list(_strings(values.get("permissions", ()))),
        "denied_permissions": list(_strings(values.get("denied_permissions", ()))),
        "inherited_roles": list(_strings(values.get("inherited_roles", ()))),
        "status": str(values.get("status", "active")),
    }
    existing = await first_table_record(Role, db, filters)
    if existing is None:
        return await create_table_record(Role, db, payload)
    return await update_table_record(Role, db, record_identifier(existing), payload)


async def list_roles_for_tenant(ctx: Mapping[str, Any]) -> tuple[object, ...]:
    values = dict(payload_from_context(ctx))
    tenant_id = values.get("tenant_id")
    rows = await list_table_records(Role, database_from_context(ctx))
    return tuple(
        row for row in rows if field_value(row, "tenant_id") in {None, tenant_id}
    )


async def upsert_attribute_policy(
    ctx: Mapping[str, Any],
) -> tuple[object, list[object]]:
    values = dict(payload_from_context(ctx))
    db = database_from_context(ctx)
    filters = {
        "name": values["name"],
        "tenant_id": values.get("tenant_id"),
    }
    existing = await first_table_record(AttributePolicy, db, filters)
    payload = {
        "name": values["name"],
        "tenant_id": values.get("tenant_id"),
        "client_id": values.get("client_id"),
        "permission": values["permission"],
        "effect": str(values.get("effect", "allow")),
        "required_attributes": dict(values.get("required_attributes") or {}),
        "status": "active",
    }
    if existing is None:
        row = await create_table_record(AttributePolicy, db, payload)
    else:
        row = await update_table_record(
            AttributePolicy, db, record_identifier(existing), payload
        )
    policy_id = record_identifier(row)
    await clear_table_records(PolicyCondition, db, {"policy_id": policy_id})
    conditions = [
        await create_table_record(
            PolicyCondition,
            db,
            {"policy_id": policy_id, **dict(condition)},
        )
        for condition in values.get("dynamic_conditions", ())
    ]
    return row, conditions


async def list_active_attribute_policies(
    ctx: Mapping[str, Any],
) -> tuple[tuple[object, list[object]], ...]:
    values = dict(payload_from_context(ctx))
    filters: dict[str, Any] = {"status": "active"}
    if values.get("tenant_id") is not None:
        filters["tenant_id"] = values["tenant_id"]
    db = database_from_context(ctx)
    rows = await list_table_records(AttributePolicy, db, filters)
    collected = []
    for row in rows:
        conditions = await list_table_records(
            PolicyCondition, db, {"policy_id": record_identifier(row)}
        )
        collected.append((row, conditions))
    return tuple(collected)


async def grant_delegated_scope(ctx: Mapping[str, Any]) -> object:
    values = dict(payload_from_context(ctx))
    db = database_from_context(ctx)
    subject = str(values.pop("subject"))
    payload = {"subject": subject, "status": "active", **values}
    existing = await first_table_record(DelegatedAdminScope, db, {"subject": subject})
    if existing is None:
        return await create_table_record(DelegatedAdminScope, db, payload)
    return await update_table_record(
        DelegatedAdminScope, db, record_identifier(existing), payload
    )


async def revoke_delegated_scope(ctx: Mapping[str, Any]) -> object:
    subject = str(payload_from_context(ctx).get("subject") or "")
    db = database_from_context(ctx)
    existing = await first_table_record(DelegatedAdminScope, db, {"subject": subject})
    if existing is None:
        raise LookupError(subject)
    return await update_table_record(
        DelegatedAdminScope,
        db,
        record_identifier(existing),
        {"status": "revoked"},
    )


async def delegated_scope_for_subject(ctx: Mapping[str, Any]) -> object | None:
    subject = str(payload_from_context(ctx).get("subject") or "")
    return await first_table_record(
        DelegatedAdminScope,
        database_from_context(ctx),
        {"subject": subject},
    )


async def list_active_delegated_scopes(
    ctx: Mapping[str, Any],
) -> tuple[object, ...]:
    rows = await list_table_records(
        DelegatedAdminScope,
        database_from_context(ctx),
        {"status": "active"},
    )
    return tuple(rows)


__all__ = [
    "assign_role",
    "delegated_scope_for_subject",
    "grant_delegated_scope",
    "grant_membership",
    "list_active_attribute_policies",
    "list_active_delegated_scopes",
    "list_roles_for_tenant",
    "revoke_delegated_scope",
    "role_names_for_principal",
    "upsert_role",
    "upsert_attribute_policy",
]
