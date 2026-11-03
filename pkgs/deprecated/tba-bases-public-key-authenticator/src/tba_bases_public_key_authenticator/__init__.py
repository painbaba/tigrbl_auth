"""Compatibility facade for :mod:`tba_bases_public_key_authentication`."""

import warnings as _warnings

_warnings.warn(
    "tba-bases-public-key-authenticator is deprecated; install tba-bases-public-key-authentication and import tba_bases_public_key_authentication instead.",
    DeprecationWarning,
    stacklevel=2,
)


from tba_bases_public_key_authentication import *  # noqa: F401,F403
from tba_bases_public_key_authentication import __all__
