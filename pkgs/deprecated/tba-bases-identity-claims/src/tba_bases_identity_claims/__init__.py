"""Compatibility facade for :mod:`tba_bases_claim`."""

import warnings as _warnings

_warnings.warn(
    "tba-bases-identity-claims is deprecated; install tba-bases-claim and import tba_bases_claim instead.",
    DeprecationWarning,
    stacklevel=2,
)


from tba_bases_claim import *  # noqa: F401,F403
from tba_bases_claim import __all__
