"""Compatibility re-export of :mod:`tba_storage_release_governance.tables.release_authorization_state._table`; tables are owned there."""

import tba_storage_release_governance.tables.release_authorization_state._table as _owner
from tba_storage_release_governance.tables.release_authorization_state._table import *  # noqa: F401,F403

__all__ = getattr(_owner, "__all__", [name for name in dir(_owner) if not name.startswith("_")])

def __getattr__(name):
    return getattr(_owner, name)
