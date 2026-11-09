"""RFC 8785 canonical JSON serialization."""

import json
from typing import Any

import rfc8785


def canonicalize(value: Any) -> bytes:
    """Return RFC 8785 canonical JSON encoded as UTF-8."""
    try:
        return rfc8785.dumps(value)
    except rfc8785.CanonicalizationError as exc:
        raise ValueError(str(exc)) from exc


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object member: {key!r}")
        result[key] = value
    return result


def canonicalize_json(document: str | bytes | bytearray) -> bytes:
    """Parse JSON with duplicate-name rejection and emit canonical bytes."""
    if isinstance(document, (bytes, bytearray)):
        document = bytes(document).decode("utf-8")
    return canonicalize(json.loads(document, object_pairs_hook=_unique_pairs))


__all__ = ["canonicalize", "canonicalize_json"]
