"""Deterministic JSON helpers and legacy JCS compatibility exports."""

from __future__ import annotations

import json
import math
import re
import hashlib
import warnings
from collections.abc import Iterable, Mapping, Sequence
from decimal import Decimal
from typing import Any

RFC8785_SPEC_URL = "https://www.rfc-editor.org/rfc/rfc8785"
MAX_SAFE_INTEGER = 2**53 - 1
_EXPONENT_RE = re.compile(r"e([+-])0+(\d+)$")


class JCSCanonicalizationError(ValueError):
    """Raised when input cannot be represented as RFC 8785 JCS JSON."""


def _warn_legacy_jcs() -> None:
    warnings.warn(
        "JCS exports in tba_primitives_identity are deprecated. "
        "Install tba-codec-jcs and import from tba_codec_jcs.",
        DeprecationWarning,
        stacklevel=3,
    )


def canonicalize(value: Any) -> bytes:
    """Return legacy canonical JSON bytes. Use tba_codec_jcs for RFC 8785."""
    _warn_legacy_jcs()
    return _serialize(value).encode("utf-8")


def canonicalize_json(document: str | bytes | bytearray) -> bytes:
    """Parse and serialize with the legacy JCS implementation."""
    _warn_legacy_jcs()

    if isinstance(document, (bytes, bytearray)):
        document = bytes(document).decode("utf-8")
    value = json.loads(document, object_pairs_hook=_reject_duplicate_pairs)
    return _serialize(value).encode("utf-8")


def _normalize_canonical_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _normalize_canonical_json_value(item)
            for key, item in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, tuple):
        return [_normalize_canonical_json_value(item) for item in value]
    if isinstance(value, list):
        return [_normalize_canonical_json_value(item) for item in value]
    if isinstance(value, set):
        return [
            _normalize_canonical_json_value(item)
            for item in sorted(value, key=lambda item: repr(item))
        ]
    return value


def canonical_json(value: Any) -> str:
    """Return deterministic JSON text for policy proof artifacts."""

    return json.dumps(
        _normalize_canonical_json_value(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def canonical_json_bytes(value: Any) -> bytes:
    """Return deterministic JSON encoded as UTF-8 bytes."""

    return canonical_json(value).encode("utf-8")


def canonical_hash(value: Any) -> str:
    """Return the SHA-256 hex digest of :func:`canonical_json` output."""

    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _reject_duplicate_pairs(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise JCSCanonicalizationError(f"duplicate JSON object member: {key!r}")
        result[key] = value
    return result


def _serialize(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        _reject_lone_surrogates(value)
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, int):
        _validate_integer(value)
        return str(value)
    if isinstance(value, float):
        return _serialize_float(value)
    if isinstance(value, Decimal):
        raise JCSCanonicalizationError("Decimal values are not JCS JSON numbers")
    if isinstance(value, Mapping):
        return _serialize_object(value)
    if _is_json_sequence(value):
        return "[" + ",".join(_serialize(item) for item in value) + "]"
    raise JCSCanonicalizationError(
        f"unsupported JCS JSON value: {type(value).__name__}"
    )


def _serialize_object(value: Mapping[Any, Any]) -> str:
    items: list[tuple[str, Any]] = []
    seen: set[str] = set()
    for key, item in value.items():
        if not isinstance(key, str):
            raise JCSCanonicalizationError("JCS object member names must be strings")
        if key in seen:
            raise JCSCanonicalizationError(f"duplicate JSON object member: {key!r}")
        _reject_lone_surrogates(key)
        seen.add(key)
        items.append((key, item))
    fields = (
        f"{_serialize(key)}:{_serialize(item)}"
        for key, item in sorted(items, key=lambda pair: _utf16_sort_key(pair[0]))
    )
    return "{" + ",".join(fields) + "}"


def _is_json_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    )


def _validate_integer(value: int) -> None:
    if abs(value) > MAX_SAFE_INTEGER:
        raise JCSCanonicalizationError(
            "JCS integer values must be exactly representable by IEEE 754 doubles"
        )


def _serialize_float(value: float) -> str:
    if not math.isfinite(value):
        raise JCSCanonicalizationError("NaN and Infinity are not valid JCS numbers")
    if value == 0:
        return "0"
    if value.is_integer() and abs(value) <= MAX_SAFE_INTEGER:
        return str(int(value))
    encoded = json.dumps(value, allow_nan=False, separators=(",", ":"))
    return _EXPONENT_RE.sub(r"e\1\2", encoded)


def _reject_lone_surrogates(value: str) -> None:
    for char in value:
        codepoint = ord(char)
        if 0xD800 <= codepoint <= 0xDFFF:
            raise JCSCanonicalizationError("lone surrogate values are not valid JCS")


def _utf16_sort_key(value: str) -> tuple[int, ...]:
    return tuple(value.encode("utf-16-be"))


__all__ = [
    "JCSCanonicalizationError",
    "MAX_SAFE_INTEGER",
    "RFC8785_SPEC_URL",
    "canonical_hash",
    "canonical_json",
    "canonical_json_bytes",
    "canonicalize",
    "canonicalize_json",
]
