"""Compatibility re-export of :mod:`tba_storage_security_event.tables.security_event_state`; tables are owned there."""

import tba_storage_security_event.tables.security_event_state as _owner
from tba_storage_security_event.tables.security_event_state import *  # noqa: F401,F403

__all__ = getattr(_owner, "__all__", [name for name in dir(_owner) if not name.startswith("_")])

def __getattr__(name):
    return getattr(_owner, name)
