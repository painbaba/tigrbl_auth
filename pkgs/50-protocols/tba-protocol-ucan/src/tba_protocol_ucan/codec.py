"""Canonical UCAN encoding for the Ed25519 development profile."""

from hashlib import sha256

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

import tba_codec_dag_cbor as dag_cbor
from tba_codec_cid import Cid
from tba_codec_dag_cbor import CBORTag
from tba_codec_multibase import decode_base58btc, encode_base58btc

from .versions import DELEGATION_TAG, INVOCATION_TAG

# Varsig v1, EdDSA, Ed25519 public key, SHA-512, DAG-CBOR.
VARSIG_HEADER = bytes.fromhex("3401ed01ed011371")
# CIDv1, dag-cbor, sha2-256, digest length 32.
_CID_CODEC = 0x71
_CID_HASH = 0x12
_ED25519_PREFIX = bytes.fromhex("ed01")
_MAX_BYTES = 64 * 1024
_MAX_DEPTH = 32


class UcanError(ValueError):
    """Malformed or unauthorized UCAN within the supported profile."""


def _decode_multibase(text: str, prefix: bytes, size: int) -> bytes:
    if not isinstance(text, str) or not text.startswith("z") or len(text) > 60:
        raise UcanError("expected base58btc multibase")
    try:
        data = decode_base58btc(text)
    except ValueError as exc:
        raise UcanError("invalid base58btc character") from exc
    if not data.startswith(prefix) or len(data) != size:
        raise UcanError("unexpected multicodec or key/digest length")
    return data


def did_key(public_key: Ed25519PublicKey) -> str:
    """Return the self-certifying DID for an Ed25519 public key."""
    return "did:key:" + encode_base58btc(
        _ED25519_PREFIX + public_key.public_bytes_raw()
    )


def _public_key(did: str) -> Ed25519PublicKey:
    if not isinstance(did, str) or not did.startswith("did:key:"):
        raise UcanError("expected an Ed25519 did:key")
    data = _decode_multibase(did[8:], _ED25519_PREFIX, 34)
    return Ed25519PublicKey.from_public_bytes(data[2:])


def validate_did(did: str) -> None:
    _public_key(did)


def content_id(wire: bytes) -> str:
    """Compute the CID of canonical bytes, without verifying their signature."""
    return Cid(1, _CID_CODEC, _CID_HASH, sha256(wire).digest()).to_text()


def _validate_cid(cid: Cid) -> Cid:
    if (cid.version, cid.codec, cid.hash_code, len(cid.digest)) != (
        1,
        _CID_CODEC,
        _CID_HASH,
        32,
    ):
        raise UcanError("expected a UCAN CIDv1 with DAG-CBOR and SHA-256")
    return cid


def cid_link(cid: str) -> CBORTag:
    if not isinstance(cid, str) or len(cid) > 60:
        raise UcanError("expected a bounded UCAN CID")
    try:
        decoded = Cid.from_text(cid)
    except ValueError as exc:
        raise UcanError("invalid UCAN CID") from exc
    return dag_cbor.cid_link(_validate_cid(decoded))


def link_cid(link: object) -> str:
    try:
        cid = dag_cbor.link_cid(link)
    except ValueError as exc:
        raise UcanError("expected a DAG-CBOR link to a UCAN CID") from exc
    return _validate_cid(cid).to_text()


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
    if isinstance(value, CBORTag):
        link_cid(value)
        return
    raise UcanError("unsupported DAG-CBOR value in the development profile")


def canonical_bytes(value: object) -> bytes:
    _validate_node(value)
    try:
        wire = dag_cbor.encode(value, max_depth=_MAX_DEPTH)
    except ValueError as exc:
        raise UcanError("cannot encode DAG-CBOR value") from exc
    if len(wire) > _MAX_BYTES:
        raise UcanError("UCAN byte limit exceeded")
    return wire


def _decode(wire: bytes) -> object:
    if type(wire) is not bytes or len(wire) > _MAX_BYTES:
        raise UcanError("expected a bounded UCAN byte string")
    try:
        value = dag_cbor.decode(wire, max_depth=_MAX_DEPTH)
    except ValueError as exc:
        raise UcanError(str(exc)) from exc
    _validate_node(value)
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
