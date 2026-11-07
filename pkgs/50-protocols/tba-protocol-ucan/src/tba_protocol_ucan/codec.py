"""Canonical UCAN encoding for the Ed25519 development profile."""

from hashlib import sha256

import cbor2
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .versions import DELEGATION_TAG, INVOCATION_TAG

# Varsig v1, EdDSA, Ed25519 public key, SHA-512, DAG-CBOR.
VARSIG_HEADER = bytes.fromhex("3401ed01ed011371")
# CIDv1, dag-cbor, sha2-256, digest length 32.
_CID_PREFIX = bytes.fromhex("01711220")
_ED25519_PREFIX = bytes.fromhex("ed01")
_BASE58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_MAX_BYTES = 64 * 1024
_MAX_DEPTH = 32


class UcanError(ValueError):
    """Malformed or unauthorized UCAN within the supported profile."""


def _base58_encode(data: bytes) -> str:
    value = int.from_bytes(data, "big")
    chars = []
    while value:
        value, remainder = divmod(value, 58)
        chars.append(_BASE58[remainder])
    leading_zeros = len(data) - len(data.lstrip(b"\x00"))
    return "1" * leading_zeros + "".join(reversed(chars))


def _decode_multibase(text: str, prefix: bytes, size: int) -> bytes:
    if not isinstance(text, str) or not text.startswith("z") or len(text) > 60:
        raise UcanError("expected base58btc multibase")
    value = 0
    try:
        for char in text[1:]:
            value = value * 58 + _BASE58.index(char)
    except ValueError as exc:
        raise UcanError("invalid base58btc character") from exc
    data = value.to_bytes((value.bit_length() + 7) // 8, "big")
    if (
        not data.startswith(prefix)
        or len(data) != size
        or "z" + _base58_encode(data) != text
    ):
        raise UcanError("unexpected multicodec or key/digest length")
    return data


def did_key(public_key: Ed25519PublicKey) -> str:
    """Return the self-certifying DID for an Ed25519 public key."""
    return "did:key:z" + _base58_encode(_ED25519_PREFIX + public_key.public_bytes_raw())


def _public_key(did: str) -> Ed25519PublicKey:
    if not isinstance(did, str) or not did.startswith("did:key:"):
        raise UcanError("expected an Ed25519 did:key")
    data = _decode_multibase(did[8:], _ED25519_PREFIX, 34)
    return Ed25519PublicKey.from_public_bytes(data[2:])


def validate_did(did: str) -> None:
    _public_key(did)


def content_id(wire: bytes) -> str:
    """Compute the CID of canonical bytes, without verifying their signature."""
    return "z" + _base58_encode(_CID_PREFIX + sha256(wire).digest())


def cid_link(cid: str) -> cbor2.CBORTag:
    data = _decode_multibase(cid, _CID_PREFIX, 36)
    return cbor2.CBORTag(42, b"\x00" + data)


def link_cid(link: object) -> str:
    if (
        not isinstance(link, cbor2.CBORTag)
        or link.tag != 42
        or type(link.value) is not bytes
        or len(link.value) != 37
        or not link.value.startswith(b"\x00" + _CID_PREFIX)
    ):
        raise UcanError("expected a DAG-CBOR link to a UCAN CID")
    return "z" + _base58_encode(link.value[1:])


def _validate_node(value: object, depth: int = 0) -> None:
    if depth >= _MAX_DEPTH:
        raise UcanError("DAG-CBOR nesting limit exceeded")
    if value is None or type(value) in (bool, str, bytes):
        return
    if type(value) is int and -(2**53 - 1) <= value <= 2**53 - 1:
        return
    if type(value) in (list, tuple):
        for item in value:
            _validate_node(item, depth + 1)
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for item in value.values():
            _validate_node(item, depth + 1)
        return
    if isinstance(value, cbor2.CBORTag):
        link_cid(value)
        return
    raise UcanError("unsupported DAG-CBOR value in the development profile")


def canonical_bytes(value: object) -> bytes:
    _validate_node(value)
    try:
        wire = cbor2.dumps(value, canonical=True)
    except (cbor2.CBORError, ValueError, TypeError) as exc:
        raise UcanError("cannot encode DAG-CBOR value") from exc
    if len(wire) > _MAX_BYTES:
        raise UcanError("UCAN byte limit exceeded")
    return wire


def _decode(wire: bytes) -> object:
    if type(wire) is not bytes or len(wire) > _MAX_BYTES:
        raise UcanError("expected a bounded UCAN byte string")
    try:
        value = cbor2.loads(
            wire,
            max_depth=_MAX_DEPTH,
            allow_indefinite=False,
            allow_duplicate_keys=False,
        )
    except (cbor2.CBORError, ValueError, TypeError) as exc:
        raise UcanError("invalid DAG-CBOR") from exc
    if canonical_bytes(value) != wire:
        raise UcanError("noncanonical DAG-CBOR")
    return value


class UcanEnvelopeCodec:
    """Sign and verify the two supported UCAN v1 wire envelopes."""

    def sign(self, tag: str, payload: dict, key: Ed25519PrivateKey) -> bytes:
        if tag not in (DELEGATION_TAG, INVOCATION_TAG):
            raise UcanError("unsupported UCAN envelope tag")
        if payload.get("iss") != did_key(key.public_key()):
            raise UcanError("signing key does not match issuer")
        signed = {"h": VARSIG_HEADER, tag: payload}
        return canonical_bytes([key.sign(canonical_bytes(signed)), signed])

    def verify(self, wire: bytes, tag: str) -> dict:
        envelope = _decode(wire)
        if (
            type(envelope) is not list
            or len(envelope) != 2
            or type(envelope[0]) is not bytes
            or len(envelope[0]) != 64
            or type(envelope[1]) is not dict
            or tag not in (DELEGATION_TAG, INVOCATION_TAG)
        ):
            raise UcanError("invalid UCAN envelope")
        signature, signed = envelope
        if (
            set(signed) != {"h", tag}
            or signed["h"] != VARSIG_HEADER
            or type(signed[tag]) is not dict
        ):
            raise UcanError("unexpected UCAN tag or Varsig header")
        payload = signed[tag]
        try:
            _public_key(payload.get("iss")).verify(signature, canonical_bytes(signed))
        except InvalidSignature as exc:
            raise UcanError("invalid UCAN signature") from exc
        return payload
