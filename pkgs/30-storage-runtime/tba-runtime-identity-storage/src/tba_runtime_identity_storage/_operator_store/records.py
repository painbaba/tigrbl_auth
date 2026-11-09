from __future__ import annotations

# ruff: noqa: F403,F405
from .paths import *
from .paths import (
    _OPERATOR_DB_FILENAME,
    _append_jsonl_file,
    _metadata_payload,
    _write_metadata_snapshot,
)
from .app import operator_store_session
from tigrbl_concrete.records import (
    create_table_record as _create_table_record,
    first_table_record as _first_table_record,
    invoke_table_operation as _invoke_table_operation,
    field as _table_field,
    list_table_records as _list_table_records,
)
from ..sync import run_async
from tba_storage_operator.tables import OperatorActivity
from tba_storage_operator.tables import OperatorAuditEvent
from tba_storage_operator.tables import OperatorMetadata
from tba_storage_operator.tables import OperatorRecord
from tba_storage_operator.tables import OperatorTransaction


async def _upsert_operator_metadata(db: Any, key: str, value: Any) -> None:
    payload = {
        "value_json": json.dumps(value, sort_keys=True),
        "updated_at": datetime.now(timezone.utc),
    }
    existing = await _first_table_record(OperatorMetadata, db, {"key": key})
    if existing is None:
        await _create_table_record(OperatorMetadata, db, {"key": key, **payload})
    else:
        await _invoke_table_operation(
            OperatorMetadata,
            "update",
            db=db,
            payload=payload,
            # The published CRUD dispatcher reads id even for a named key.
            path_params={"id": key, "key": key},
        )


def _load_records_from_snapshot(
    path: Path, *, tenant: str | None = None
) -> dict[str, dict[str, Any]]:
    loaded = load_structured(path, default={})
    rows: dict[str, dict[str, Any]] = {}
    if isinstance(loaded, Mapping):
        items = loaded.values()
    elif isinstance(loaded, list):
        items = loaded
    else:
        items = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        record_id = item.get("id")
        if not record_id:
            continue
        if tenant is not None and item.get("tenant") != tenant:
            continue
        rows[str(record_id)] = copy.deepcopy(dict(item))
    return rows


async def _load_records_async(
    repo_root: Path, resource: str, tenant: str | None = None
) -> dict[str, dict[str, Any]]:
    state_root = operator_state_root(repo_root)
    db_path = operator_database_path(repo_root)
    had_db = db_path.exists()
    async with operator_store_session(state_root) as db:
        stored = await _list_table_records(OperatorRecord, db, {"resource": resource})
        rows = {}
        for row in stored:
            row_tenant = _table_field(row, "tenant")
            if tenant is not None and row_tenant != tenant:
                continue
            record_id = str(_table_field(row, "record_id"))
            rows[record_id] = {
                "id": record_id,
                "resource": _table_field(row, "resource"),
                "status": _table_field(row, "status"),
                "enabled": bool(_table_field(row, "enabled")),
                "created_at": _table_field(row, "created_at"),
                "updated_at": _table_field(row, "updated_at"),
                "actor": _table_field(row, "actor"),
                "profile": _table_field(row, "profile"),
                "tenant": row_tenant,
                "issuer": _table_field(row, "issuer"),
                "revision": int(_table_field(row, "revision") or 1),
                "data": json.loads(_table_field(row, "data_json") or "{}"),
            }
    if rows or had_db or db_path.exists():
        return rows
    return _load_records_from_snapshot(
        resource_state_path(repo_root, resource), tenant=tenant
    )


def load_records(
    repo_root: Path, resource: str, tenant: str | None = None
) -> dict[str, dict[str, Any]]:
    return run_async(_load_records_async(repo_root, resource, tenant=tenant))


def default_status(resource: str) -> str:
    if resource in {"keys"}:
        return "staged"
    return "active"


def deep_merge(base: Mapping[str, Any], patch: Mapping[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(dict(base))
    for key, value in patch.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), Mapping):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def make_record(
    resource: str,
    record_id: str,
    context: OperationContext,
    patch: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    patch = dict(patch or {})
    now = utc_now()
    data = copy.deepcopy(dict(patch))
    if context.tenant is None and data.get("tenant") is not None:
        tenant = str(data.pop("tenant"))
    else:
        tenant = context.tenant
    status = str(data.pop("status", default_status(resource)))
    enabled = bool(
        data.pop("enabled", status not in {"disabled", "revoked", "retired", "locked"})
    )
    return {
        "id": str(record_id),
        "resource": resource,
        "status": status,
        "enabled": enabled,
        "created_at": now,
        "updated_at": now,
        "actor": context.actor,
        "profile": context.profile,
        "tenant": tenant,
        "issuer": context.issuer,
        "revision": 1,
        "data": data,
    }


def matches_record(record: Mapping[str, Any], spec: FilterSpec) -> bool:
    if spec.status_filter and str(record.get("status")) != str(spec.status_filter):
        return False
    if spec.filter_expr:
        term = str(spec.filter_expr).strip().lower()
        haystacks = [
            str(record.get("id", "")).lower(),
            str(record.get("status", "")).lower(),
            str(record.get("tenant", "")).lower(),
            json.dumps(record.get("data", {}), sort_keys=True).lower(),
        ]
        data = record.get("data") or {}
        if isinstance(data, Mapping):
            for key in (
                "name",
                "display_name",
                "tenant_id",
                "client_id",
                "username",
                "email",
                "kid",
                "software_id",
            ):
                haystacks.append(str(data.get(key, "")).lower())
        if not any(term in item for item in haystacks):
            return False
    return True


def sort_records(
    records: list[dict[str, Any]], sort_key: str = "id"
) -> list[dict[str, Any]]:
    def _sort_value(item: Mapping[str, Any]) -> tuple[str, str]:
        data = item.get("data") if isinstance(item.get("data"), Mapping) else {}
        primary = data.get(sort_key, item.get(sort_key, ""))
        return (str(primary or ""), str(item.get("id", "")))

    return [copy.deepcopy(dict(item)) for item in sorted(records, key=_sort_value)]


def list_records(
    repo_root: Path,
    resource: str,
    spec: FilterSpec | None = None,
    tenant: str | None = None,
) -> list[dict[str, Any]]:
    spec = spec or FilterSpec()
    records = load_records(repo_root, resource, tenant=tenant).values()
    filtered = [
        copy.deepcopy(dict(item)) for item in records if matches_record(item, spec)
    ]
    sorted_items = sort_records(filtered, spec.sort)
    return sorted_items[spec.offset : spec.offset + spec.limit]


def latest_event(repo_root: Path, *, predicate=None) -> dict[str, Any] | None:
    items = sorted(
        read_jsonl(audit_log_path(repo_root)),
        key=lambda item: str(item.get("occurred_at", "")),
        reverse=True,
    )
    if predicate is None:
        return items[0] if items else None
    for item in items:
        try:
            if predicate(item):
                return item
        except Exception:
            continue
    return None


def build_transaction_entry(
    context: OperationContext,
    *,
    status: str,
    record_id: str | None = None,
    changed_ids: list[str] | None = None,
    summary: Mapping[str, Any] | None = None,
    before_checksum: str | None = None,
    after_checksum: str | None = None,
) -> dict[str, Any]:
    return {
        "transaction_id": synthetic_id("txn"),
        "ts": utc_now(),
        "command": context.command,
        "resource": context.resource,
        "status": status,
        "record_id": record_id,
        "changed_ids": list(changed_ids or ([] if record_id is None else [record_id])),
        "summary": dict(summary or {}),
        "actor": context.actor,
        "profile": context.profile,
        "tenant": context.tenant,
        "issuer": context.issuer,
        "before_checksum": before_checksum,
        "after_checksum": after_checksum,
    }


def build_audit_entry(
    context: OperationContext,
    *,
    transaction_id: str,
    status: str,
    target_id: str | None = None,
    details: Mapping[str, Any] | None = None,
    source_surface: str = "operator",
) -> dict[str, Any]:
    return {
        "id": synthetic_id("audit"),
        "tenant_id": context.tenant,
        "actor_user_id": context.actor,
        "actor_client_id": None,
        "session_id": None,
        "event_type": context.command,
        "target_type": context.resource,
        "target_id": target_id,
        "outcome": status,
        "request_id": transaction_id,
        "occurred_at": utc_now(),
        "details": {**dict(details or {}), "source_surface": source_surface},
    }


def _operator_activity_record(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ts": payload.get("ts"),
        "kind": payload.get("kind"),
        "resource": payload.get("resource"),
        "record_id": payload.get("id") or payload.get("record_id"),
        "status": payload.get("status"),
        "transaction_id": payload.get("transaction_id"),
    }


def _operator_activity_rows(rows: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "seq": int(_table_field(row, "id") or 0),
            "ts": _table_field(row, "ts"),
            "kind": _table_field(row, "kind"),
            "resource": _table_field(row, "resource"),
            "id": _table_field(row, "record_id"),
            "status": _table_field(row, "status"),
            "transaction_id": _table_field(row, "transaction_id"),
        }
        for row in sorted(rows, key=lambda item: int(_table_field(item, "id") or 0))
    ]


def _operator_audit_record(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": payload.get("id"),
        "tenant_id": payload.get("tenant_id"),
        "actor_user_id": payload.get("actor_user_id"),
        "actor_client_id": payload.get("actor_client_id"),
        "session_id": payload.get("session_id"),
        "event_type": payload.get("event_type"),
        "target_type": payload.get("target_type"),
        "target_id": payload.get("target_id"),
        "outcome": payload.get("outcome"),
        "request_id": payload.get("request_id"),
        "occurred_at": payload.get("occurred_at"),
        "details_json": json.dumps(dict(payload.get("details") or {}), sort_keys=True),
    }


def _operator_audit_rows(rows: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": _table_field(row, "id"),
            "tenant_id": _table_field(row, "tenant_id"),
            "actor_user_id": _table_field(row, "actor_user_id"),
            "actor_client_id": _table_field(row, "actor_client_id"),
            "session_id": _table_field(row, "session_id"),
            "event_type": _table_field(row, "event_type"),
            "target_type": _table_field(row, "target_type"),
            "target_id": _table_field(row, "target_id"),
            "outcome": _table_field(row, "outcome"),
            "request_id": _table_field(row, "request_id"),
            "occurred_at": _table_field(row, "occurred_at"),
            "details": json.loads(_table_field(row, "details_json") or "{}"),
        }
        for row in sorted(
            rows,
            key=lambda item: (
                str(_table_field(item, "occurred_at", "")),
                str(_table_field(item, "id", "")),
            ),
        )
    ]


def _operator_transaction_record(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "transaction_id": payload.get("transaction_id"),
        "ts": payload.get("ts"),
        "command": payload.get("command"),
        "resource": payload.get("resource"),
        "status": payload.get("status"),
        "record_id": payload.get("record_id"),
        "changed_ids_json": json.dumps(
            list(payload.get("changed_ids") or []), sort_keys=True
        ),
        "summary_json": json.dumps(dict(payload.get("summary") or {}), sort_keys=True),
        "actor": payload.get("actor"),
        "profile": payload.get("profile"),
        "tenant": payload.get("tenant"),
        "issuer": payload.get("issuer"),
        "before_checksum": payload.get("before_checksum"),
        "after_checksum": payload.get("after_checksum"),
    }


def _operator_transaction_rows(rows: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "transaction_id": _table_field(row, "transaction_id"),
            "ts": _table_field(row, "ts"),
            "command": _table_field(row, "command"),
            "resource": _table_field(row, "resource"),
            "status": _table_field(row, "status"),
            "record_id": _table_field(row, "record_id"),
            "changed_ids": json.loads(_table_field(row, "changed_ids_json") or "[]"),
            "summary": json.loads(_table_field(row, "summary_json") or "{}"),
            "actor": _table_field(row, "actor"),
            "profile": _table_field(row, "profile"),
            "tenant": _table_field(row, "tenant"),
            "issuer": _table_field(row, "issuer"),
            "before_checksum": _table_field(row, "before_checksum"),
            "after_checksum": _table_field(row, "after_checksum"),
        }
        for row in sorted(
            rows,
            key=lambda item: (
                str(_table_field(item, "ts", "")),
                str(_table_field(item, "transaction_id", "")),
            ),
        )
    ]


def _sync_resource_snapshot(repo_root: Path, resource: str) -> None:
    rows = load_records(repo_root, resource, tenant=None)
    write_structured(resource_state_path(repo_root, resource), rows, fmt="json")
    _write_metadata_snapshot(repo_root)


from . import mutation as _mutation
from .mutation import *  # noqa: F401,F403

__all__ = _mutation.__all__
