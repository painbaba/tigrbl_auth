"""Deprecated import compatibility for the former Swarmauri JOSE provider."""

import warnings as _warnings

_warnings.warn(
    "tba-provider-jose-swarmauri is deprecated; install tba-provider-identity-jose and import tba_provider_identity_jose instead.",
    DeprecationWarning,
    stacklevel=2,
)


from .jwks_publication import build_combined_jwks_document
from .key_management import *
from .oidc_key_runtime import *
from .pqc import *

__all__ = [name for name in globals() if not name.startswith("_")]
