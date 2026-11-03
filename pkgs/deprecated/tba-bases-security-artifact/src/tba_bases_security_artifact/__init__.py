"""Compatibility facade for :mod:`tba_bases_protected_artifact`."""

import warnings as _warnings

_warnings.warn(
    "tba-bases-security-artifact is deprecated; install tba-bases-protected-artifact and import tba_bases_protected_artifact instead.",
    DeprecationWarning,
    stacklevel=2,
)


from tba_bases_protected_artifact import *  # noqa: F401,F403
from tba_bases_protected_artifact import __all__
