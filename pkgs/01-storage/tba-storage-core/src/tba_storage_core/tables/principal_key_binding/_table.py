"""Compatibility re-export of :mod:`tba_storage_key_material.tables.principal_key_binding._table`; tables are owned there."""

import tba_storage_key_material.tables.principal_key_binding._table as _owner
from tba_storage_key_material.tables.principal_key_binding._table import *  # noqa: F401,F403

__all__ = getattr(_owner, "__all__", [name for name in dir(_owner) if not name.startswith("_")])

def __getattr__(name):
    return getattr(_owner, name)
