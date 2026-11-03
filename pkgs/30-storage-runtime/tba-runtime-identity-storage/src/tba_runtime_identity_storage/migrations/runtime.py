"""Executable migration runner and schema verification helpers."""

from __future__ import annotations

import importlib.util
import importlib.metadata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tigrbl_concrete.ddl import bootstrap_dbschema
from tigrbl_concrete.ddl import sqlite_default_attach_map
from tba_storage_core.migrations.helpers import (
    applied_revisions,
    column_names,
    mark_revision,
    table_names,
    unmark_revision,
)
from tba_storage_core.migrations.helpers import AUTHN_SCHEMA
from tba_primitives_identity.orm import RestOltpTable
from tba_storage_core.components import load_full_composition
from tigrbl_migrations import MigrationLedger, MigrationOrchestrator
from ..engine import ENGINE


def _versions_dir() -> Path:
    spec = importlib.util.find_spec("tba_storage_core.migrations.versions")
    locations = list(spec.submodule_search_locations or ()) if spec is not None else []
    if not locations:
        raise RuntimeError(
            "Unable to resolve tba_storage_core migration versions directory"
        )
    return Path(locations[0])


VERSIONS_DIR = _versions_dir()


@dataclass(slots=True)
class MigrationResult:
    applied: list[str]
    pending_before: list[str]
    expected_tables: list[str]
    actual_tables: list[str]
    missing_tables: list[str]
    passed: bool


@dataclass(slots=True)
class SchemaVerification:
    passed: bool
    expected_tables: list[str]
    actual_tables: list[str]
    missing_tables: list[str]
    unexpected_tables: list[str]


def _resolve_provider():
    try:
        from tigrbl_concrete.engine import resolver as engine_resolver

        provider = engine_resolver.resolve_provider()
        if provider is not None:
            return provider
    except Exception:
        pass

    return ENGINE.provider


def _load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load migration module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def iter_migration_modules() -> list[Any]:
    return [
        _load_module(path)
        for path in sorted(VERSIONS_DIR.glob("*.py"))
        if path.name != "__init__.py"
    ]


def expected_table_names() -> list[str]:
    names: list[str] = []
    for table in sorted(
        RestOltpTable.metadata.sorted_tables, key=lambda item: item.name
    ):
        if table.schema == "authn":
            names.append(table.name)
    return names


def _bootstrap_sqlite_schema(raw_engine: Any) -> dict[str, str]:
    dialect = getattr(getattr(raw_engine, "dialect", None), "name", "")
    if dialect != "sqlite":
        return {}
    attachments = sqlite_default_attach_map(raw_engine, (AUTHN_SCHEMA,))
    bootstrap_dbschema(
        raw_engine,
        schemas=(AUTHN_SCHEMA,),
        sqlite_attachments=attachments,
        immediate=False,
    )
    return attachments


def _ensure_sqlite_attachment_on_connection(
    sync_conn: Any, attachments: dict[str, str]
) -> None:
    if sync_conn.dialect.name != "sqlite" or not attachments:
        return
    existing = {
        str(row[1])
        for row in sync_conn.exec_driver_sql("PRAGMA database_list").fetchall()
    }
    for schema, path in attachments.items():
        if not path or schema in existing:
            continue
        try:
            sync_conn.exec_driver_sql(f'ATTACH DATABASE ? AS "{schema}"', (path,))
        except Exception:
            safe_path = path.replace("'", "''")
            sync_conn.exec_driver_sql(f"ATTACH DATABASE '{safe_path}' AS \"{schema}\"")


def verify_schema_sync(conn) -> SchemaVerification:
    expected = expected_table_names()
    actual = sorted(table_names(conn))
    expected_set = set(expected)
    actual_set = set(actual)
    missing = sorted(expected_set - actual_set)
    unexpected = sorted(actual_set - expected_set - {"schema_migrations"})
    return SchemaVerification(
        passed=not missing,
        expected_tables=expected,
        actual_tables=actual,
        missing_tables=missing,
        unexpected_tables=unexpected,
    )


def column_names_sync(conn, table: str) -> list[str]:
    return sorted(column_names(conn, table))


async def apply_all_async() -> MigrationResult:
    provider = _resolve_provider()
    raw_engine, _ = provider.ensure()
    attachments = _bootstrap_sqlite_schema(raw_engine)

    def _upgrade(sync_conn):
        _ensure_sqlite_attachment_on_connection(sync_conn, attachments)
        modules = iter_migration_modules()
        current = applied_revisions(sync_conn)
        pending_before: list[str] = []
        applied_now: list[str] = []
        if current and "0038_adopt_component_ownership" not in current:
            legacy_pending = [
                module for module in modules if module.revision not in current
            ]
            pending_before.extend(module.revision for module in legacy_pending)
            for module in legacy_pending:
                module.upgrade(sync_conn)
                mark_revision(sync_conn, module.revision)
                applied_now.append(module.revision)

        composition, migrations = load_full_composition()
        artifact_versions = {
            manifest.component_id: importlib.metadata.version(manifest.distribution)
            for manifest in composition.manifests
        }
        orchestrator = MigrationOrchestrator(
            composition=composition,
            migrations=migrations,
            ledger=MigrationLedger(sync_conn),
            artifact_versions=artifact_versions,
        )
        component_plan = orchestrator.plan()
        pending_before.extend(item.revision for item in component_plan.ordered)
        applied_now.extend(item.revision for item in orchestrator.apply().ordered)
        verification = verify_schema_sync(sync_conn)
        return MigrationResult(
            applied=applied_now,
            pending_before=pending_before,
            expected_tables=verification.expected_tables,
            actual_tables=verification.actual_tables,
            missing_tables=verification.missing_tables,
            passed=verification.passed,
        )

    begin_ctx = raw_engine.begin()
    if hasattr(begin_ctx, "__aenter__"):
        async with begin_ctx as conn:
            return await conn.run_sync(_upgrade)
    with begin_ctx as conn:
        return _upgrade(conn)


async def downgrade_one_async() -> str | None:
    provider = _resolve_provider()
    raw_engine, _ = provider.ensure()
    attachments = _bootstrap_sqlite_schema(raw_engine)

    def _downgrade(sync_conn):
        _ensure_sqlite_attachment_on_connection(sync_conn, attachments)
        modules = iter_migration_modules()
        applied = applied_revisions(sync_conn)
        for module in reversed(modules):
            if module.revision in applied:
                module.downgrade(sync_conn)
                unmark_revision(sync_conn, module.revision)
                remaining = applied_revisions(sync_conn)
                for candidate in reversed(modules):
                    if candidate.revision in remaining:
                        return candidate.revision
                return None
        return None

    begin_ctx = raw_engine.begin()
    if hasattr(begin_ctx, "__aenter__"):
        async with begin_ctx as conn:
            return await conn.run_sync(_downgrade)
    with begin_ctx as conn:
        return _downgrade(conn)


async def verify_schema_async() -> SchemaVerification:
    provider = _resolve_provider()
    raw_engine, _ = provider.ensure()
    attachments = _bootstrap_sqlite_schema(raw_engine)
    begin_ctx = raw_engine.begin()
    if hasattr(begin_ctx, "__aenter__"):
        async with begin_ctx as conn:
            return await conn.run_sync(
                lambda sync_conn: (
                    _ensure_sqlite_attachment_on_connection(sync_conn, attachments),
                    verify_schema_sync(sync_conn),
                )[1]
            )
    with begin_ctx as conn:
        _ensure_sqlite_attachment_on_connection(conn, attachments)
        return verify_schema_sync(conn)


async def column_names_async(table: str) -> list[str]:
    provider = _resolve_provider()
    raw_engine, _ = provider.ensure()
    attachments = _bootstrap_sqlite_schema(raw_engine)
    begin_ctx = raw_engine.begin()
    if hasattr(begin_ctx, "__aenter__"):
        async with begin_ctx as conn:
            return await conn.run_sync(
                lambda sync_conn: (
                    _ensure_sqlite_attachment_on_connection(sync_conn, attachments),
                    column_names_sync(sync_conn, table),
                )[1]
            )
    with begin_ctx as conn:
        _ensure_sqlite_attachment_on_connection(conn, attachments)
        return column_names_sync(conn, table)


__all__ = [
    "MigrationResult",
    "SchemaVerification",
    "apply_all_async",
    "column_names_async",
    "column_names_sync",
    "downgrade_one_async",
    "expected_table_names",
    "iter_migration_modules",
    "verify_schema_async",
    "verify_schema_sync",
]
