"""Strict canonical DAG-CBOR with CID links."""

import math
import struct

import cbor2
from cbor2 import CBORTag
from tba_codec_cid import Cid


def cid_link(cid: Cid) -> CBORTag:
    """Encode an IPLD link as CBOR tag 42 with the binary identity prefix."""
    return CBORTag(42, b"\x00" + cid.to_bytes())


def link_cid(link: object) -> Cid:
    if (
        not isinstance(link, CBORTag)
        or link.tag != 42
        or type(link.value) is not bytes
        or not link.value.startswith(b"\x00")
    ):
        raise ValueError("expected a DAG-CBOR CID link")
    return Cid.from_bytes(link.value[1:])


def _validate(value: object, depth: int) -> None:
    if depth <= 0:
        raise ValueError("DAG-CBOR nesting limit exceeded")
    if value is None or type(value) in (bool, str, bytes):
        return
    if type(value) is int and -(2**64) <= value < 2**64:
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) in (list, tuple):
        for item in value:
            _validate(item, depth - 1)
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for item in value.values():
            _validate(item, depth - 1)
        return
    if isinstance(value, CBORTag):
        link_cid(value)
        return
    raise ValueError("unsupported DAG-CBOR value")


def _encode_float(encoder: cbor2.CBOREncoder, value: float) -> None:
    # DAG-CBOR requires binary64, even when CBOR could use fewer bytes.
    encoder.write(b"\xfb" + struct.pack(">d", value or 0.0))


def encode(value: object, *, max_depth: int = 64) -> bytes:
    """Encode a value using canonical DAG-CBOR."""
    _validate(value, max_depth)
    try:
        return cbor2.dumps(value, canonical=True, encoders={float: _encode_float})
    except (cbor2.CBORError, TypeError, UnicodeError) as exc:
        raise ValueError("cannot encode DAG-CBOR value") from exc


def decode(wire: bytes, *, max_depth: int = 64) -> object:
    """Decode a single DAG-CBOR value and reject alternate serializations."""
    if type(wire) is not bytes:
        raise ValueError("expected a DAG-CBOR byte string")
    try:
        value = cbor2.loads(
            wire,
            max_depth=max_depth,
            allow_indefinite=False,
            allow_duplicate_keys=False,
        )
    except (cbor2.CBORError, ValueError, TypeError) as exc:
        raise ValueError("invalid DAG-CBOR") from exc
    if encode(value, max_depth=max_depth) != wire:
        raise ValueError("noncanonical DAG-CBOR")
    return value


__all__ = ["CBORTag", "cid_link", "decode", "encode", "link_cid"]
