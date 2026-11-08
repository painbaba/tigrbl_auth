"""Compatibility module for RFC 8785 JSON canonicalization helpers.

RFC 8785 implementation: tba_codec_jcs.
"""

from __future__ import annotations

import warnings

from .json_canonicalization import (
    JCSCanonicalizationError,
    MAX_SAFE_INTEGER,
    RFC8785_SPEC_URL,
    canonicalize,
    canonicalize_json,
)

warnings.warn(
    "tba_primitives_identity.rfc8785 is deprecated. "
    "Install tba-codec-jcs and import from tba_codec_jcs.",
    DeprecationWarning,
    stacklevel=2,
)


__all__ = [
    "JCSCanonicalizationError",
    "MAX_SAFE_INTEGER",
    "RFC8785_SPEC_URL",
    "canonicalize",
    "canonicalize_json",
]
