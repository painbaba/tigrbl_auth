"""Compatibility re-export of :mod:`tba_storage_authorization_policy.tables.policy_set_member`; tables are owned there."""

import tba_storage_authorization_policy.tables.policy_set_member as _owner
from tba_storage_authorization_policy.tables.policy_set_member import *  # noqa: F401,F403

__all__ = getattr(_owner, "__all__", [name for name in dir(_owner) if not name.startswith("_")])

def __getattr__(name):
    return getattr(_owner, name)
