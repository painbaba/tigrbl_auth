"""Tigrbl app/session wiring for the external operator store."""

from __future__ import annotations

import inspect
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from tigrbl_concrete._concrete import TigrblRouter
from tba_storage_operator.tables import OperatorActivity
from tba_storage_operator.tables import OperatorAuditEvent
from tba_storage_operator.tables import OperatorMetadata
from tba_storage_operator.tables import OperatorRecord
from tba_storage_operator.tables import OperatorTransaction

from .paths import _OPERATOR_DB_FILENAME


OPERATOR_TABLES = (
    OperatorMetadata,
    OperatorRecord,
    OperatorTransaction,
    OperatorAuditEvent,
    OperatorActivity,
)

_APP_CACHE: dict[str, TigrblRouter] = {}


def _resolve_api_provider(api: Any) -> Any:
    from tigrbl_concrete.engine import resolver as engine_resolver

    try:
        return engine_resolver.resolve_provider(api=api)
    except TypeError:
        return engine_resolver.resolve_provider(router=api)


async def operator_store_app(state_root: Path) -> TigrblRouter:
    key = str(state_root.resolve())
    cached = _APP_CACHE.get(key)
    if cached is not None:
        return cached
    state_root.mkdir(parents=True, exist_ok=True)
    (state_root / "logs").mkdir(parents=True, exist_ok=True)
    (state_root / "snapshots").mkdir(parents=True, exist_ok=True)
    db_path = state_root / _OPERATOR_DB_FILENAME
    app = TigrblRouter(engine=f"sqlite+aiosqlite:///{db_path}")
    for table in OPERATOR_TABLES:
        app.include_table(table)
    init = app.initialize()
    if inspect.isawaitable(init):
        await init
    _APP_CACHE[key] = app
    return app


async def operator_store_provider(state_root: Path) -> Any:
    app = await operator_store_app(state_root)
    provider = _resolve_api_provider(app)
    if provider is None:
        raise RuntimeError("operator store app did not expose a Tigrbl engine provider")
    return provider


@asynccontextmanager
async def operator_store_session(state_root: Path) -> AsyncIterator[Any]:
    provider = await operator_store_provider(state_root)
    _, maker = provider.ensure()
    async with maker() as session:
        try:
            yield session
            commit = getattr(session, "commit", None)
            if callable(commit):
                result = commit()
                if hasattr(result, "__await__"):
                    await result
        except Exception:
            rollback = getattr(session, "rollback", None)
            if callable(rollback):
                result = rollback()
                if hasattr(result, "__await__"):
                    await result
            raise


__all__ = [
    "OPERATOR_TABLES",
    "operator_store_app",
    "operator_store_provider",
    "operator_store_session",
]
