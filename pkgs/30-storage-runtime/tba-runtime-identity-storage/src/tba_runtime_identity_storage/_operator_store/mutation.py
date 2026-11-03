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
    delete_table_record as _delete_table_record,
    field as _table_field,
    list_table_records as _list_table_records,
)
from ..sync import run_async
from tba_storage_operator.tables import OperatorActivity
from tba_storage_operator.tables import OperatorAuditEvent
from tba_storage_operator.tables import OperatorMetadata
from tba_storage_operator.tables import OperatorRecord
from tba_storage_operator.tables import OperatorTransaction


from .records import *  # noqa: F401,F403
from .records import (
    _operator_activity_record,
    _operator_activity_rows,
    _operator_audit_record,
    _operator_audit_rows,
    _operator_transaction_record,
    _operator_transaction_rows,
    _sync_resource_snapshot,
    _upsert_operator_metadata,
)
from .paths import _jsonl_rows


async def _commit_mutation_async(
    context: OperationContext,
    *,
    records: Mapping[str, Mapping[str, Any]],
    transaction: Mapping[str, Any],
    audit_entry: Mapping[str, Any] | None = None,
) -> None:
    root = operator_state_root(context.repo_root)
    async with operator_store_session(root) as db:
        if not context.dry_run:
            stored = await _list_table_records(
                OperatorRecord, db, {"resource": context.resource}
            )
            for row in stored:
                if (
                    context.tenant is not None
                    and _table_field(row, "tenant") != context.tenant
                ):
                    continue
                await _delete_table_record(OperatorRecord, db, _table_field(row, "id"))
            for record_id, record in records.items():
                if (
                    context.tenant is not None
                    and record.get("tenant") != context.tenant
                ):
                    continue
                await _create_table_record(
                    OperatorRecord,
                    db,
                    {
                        "id": OperatorRecord.store_id(context.resource, str(record_id)),
                        "resource": context.resource,
                        "record_id": str(record_id),
                        "status": record.get(
                            "status", default_status(context.resource)
                        ),
                        "enabled": bool(record.get("enabled", True)),
                        "created_at": record.get("created_at") or utc_now(),
                        "updated_at": record.get("updated_at") or utc_now(),
                        "actor": context.actor or record.get("actor"),
                        "profile": record.get("profile"),
                        "tenant": record.get("tenant"),
                        "issuer": record.get("issuer"),
                        "revision": int(record.get("revision") or 1),
                        "data_json": json.dumps(
                            dict(record.get("data") or {}), sort_keys=True
                        ),
                    },
                )
        await _create_table_record(
            OperatorTransaction, db, _operator_transaction_record(transaction)
        )
        if audit_entry is not None:
            await _create_table_record(
                OperatorAuditEvent, db, _operator_audit_record(audit_entry)
            )
        await _create_table_record(
            OperatorActivity,
            db,
            _operator_activity_record(
                {
                    "ts": utc_now(),
                    "kind": context.command,
                    "resource": context.resource,
                    "id": transaction.get("record_id"),
                    "status": transaction.get("status"),
                    "transaction_id": transaction.get("transaction_id"),
                }
            ),
        )
        await _upsert_operator_metadata(
            db, "last_transaction_id", transaction.get("transaction_id")
        )
        await _upsert_operator_metadata(
            db, "last_transaction_status", transaction.get("status")
        )
        await _upsert_operator_metadata(db, "repo_mutation_dependency", False)


def commit_mutation(
    context: OperationContext,
    *,
    records: Mapping[str, Mapping[str, Any]],
    transaction: Mapping[str, Any],
    audit_entry: Mapping[str, Any] | None = None,
) -> None:
    run_async(
        _commit_mutation_async(
            context, records=records, transaction=transaction, audit_entry=audit_entry
        )
    )
    if not context.dry_run:
        _sync_resource_snapshot(context.repo_root, context.resource)
    _append_jsonl_file(transaction_log_path(context.repo_root), transaction)
    if audit_entry is not None:
        _append_jsonl_file(audit_log_path(context.repo_root), audit_entry)
    _append_jsonl_file(
        activity_log_path(context.repo_root),
        {
            "ts": utc_now(),
            "kind": context.command,
            "resource": context.resource,
            "id": transaction.get("record_id"),
            "status": transaction.get("status"),
            "transaction_id": transaction.get("transaction_id"),
        },
    )
    _write_metadata_snapshot(context.repo_root)


def _operator_root_from_path(path: Path) -> Path | None:
    if path.parent.name == "logs":
        return path.parent.parent
    if path.parent.name == "snapshots":
        return path.parent.parent
    return None


def _operator_table_for_log(path: Path) -> str | None:
    return {
        "transactions.jsonl": "transaction_log",
        "audit-events.jsonl": "audit_log",
        "activity.jsonl": "activity_log",
    }.get(path.name)


async def _read_operator_log_async(root: Path, table: str) -> list[dict[str, Any]]:
    async with operator_store_session(root) as db:
        if table == "transaction_log":
            return _operator_transaction_rows(
                await _list_table_records(OperatorTransaction, db)
            )
        if table == "audit_log":
            return _operator_audit_rows(
                await _list_table_records(OperatorAuditEvent, db)
            )
        return _operator_activity_rows(await _list_table_records(OperatorActivity, db))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    root = _operator_root_from_path(path)
    table = _operator_table_for_log(path)
    if (
        root is not None
        and table is not None
        and (root / _OPERATOR_DB_FILENAME).exists()
    ):
        return run_async(_read_operator_log_async(root, table))
    return _jsonl_rows(path)


async def _append_operator_log_async(
    root: Path, table: str, payload: Mapping[str, Any]
) -> None:
    async with operator_store_session(root) as db:
        if table == "transaction_log":
            await _create_table_record(
                OperatorTransaction, db, _operator_transaction_record(payload)
            )
        elif table == "audit_log":
            await _create_table_record(
                OperatorAuditEvent, db, _operator_audit_record(payload)
            )
        else:
            await _create_table_record(
                OperatorActivity, db, _operator_activity_record(payload)
            )


def append_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
    root = _operator_root_from_path(path)
    table = _operator_table_for_log(path)
    if root is not None and table is not None:
        run_async(_append_operator_log_async(root, table, payload))
        _append_jsonl_file(path, payload)
        return
    _append_jsonl_file(path, payload)


async def _ensure_operator_metadata_async(repo_root: Path) -> None:
    root = operator_state_root(repo_root)
    async with operator_store_session(root) as db:
        for key, value in _metadata_payload(repo_root).items():
            await _upsert_operator_metadata(db, key, value)


def operator_store_summary(repo_root: Path) -> dict[str, Any]:
    run_async(_ensure_operator_metadata_async(repo_root))
    _write_metadata_snapshot(repo_root)
    payload = _metadata_payload(repo_root)
    payload.update(
        {
            "database_present": operator_database_path(repo_root).exists(),
            "audit_log_path": safe_display_path(
                audit_log_path(repo_root), repo_root, external_label="<operator-state>"
            ),
            "transaction_log_path": safe_display_path(
                transaction_log_path(repo_root),
                repo_root,
                external_label="<operator-state>",
            ),
            "activity_log_path": safe_display_path(
                activity_log_path(repo_root),
                repo_root,
                external_label="<operator-state>",
            ),
        }
    )
    return payload


__all__ = [
    "ArtifactResult",
    "FilterSpec",
    "OPERATOR_STORE_SCHEMA_VERSION",
    "PORTABILITY_SCHEMA_VERSION",
    "OperationContext",
    "TransactionResult",
    "activity_log_path",
    "append_jsonl",
    "audit_log_path",
    "build_audit_entry",
    "build_transaction_entry",
    "commit_mutation",
    "deep_merge",
    "default_status",
    "display_path",
    "latest_event",
    "list_records",
    "load_records",
    "load_structured",
    "make_record",
    "matches_record",
    "operator_database_path",
    "operator_state_metadata_path",
    "operator_state_root",
    "operator_store_summary",
    "read_jsonl",
    "resource_state_path",
    "sha256_json",
    "sha256_path",
    "sort_records",
    "synthetic_id",
    "transaction_log_path",
    "utc_now",
    "validate_checksum",
    "write_structured",
]
