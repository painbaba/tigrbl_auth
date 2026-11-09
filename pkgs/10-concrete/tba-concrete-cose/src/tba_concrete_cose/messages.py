"""Deterministic RFC 9052 COSE structure decoding."""

from dataclasses import dataclass
from tba_primitives_identity.enum_compat import StrEnum
from typing import Mapping

import cbor2


class CoseMessageKind(StrEnum):
    SIGN = "COSE_Sign"
    SIGN1 = "COSE_Sign1"
    ENCRYPT = "COSE_Encrypt"
    ENCRYPT0 = "COSE_Encrypt0"
    MAC = "COSE_Mac"
    MAC0 = "COSE_Mac0"


COSE_TAG_KINDS = {
    98: CoseMessageKind.SIGN,
    18: CoseMessageKind.SIGN1,
    96: CoseMessageKind.ENCRYPT,
    16: CoseMessageKind.ENCRYPT0,
    97: CoseMessageKind.MAC,
    17: CoseMessageKind.MAC0,
}
_EXPECTED_LENGTHS = {
    CoseMessageKind.SIGN: 4,
    CoseMessageKind.SIGN1: 4,
    CoseMessageKind.ENCRYPT: 4,
    CoseMessageKind.ENCRYPT0: 3,
    CoseMessageKind.MAC: 5,
    CoseMessageKind.MAC0: 4,
}


@dataclass(frozen=True, slots=True)
class CoseMessage:
    kind: CoseMessageKind
    encoded: bytes
    protected_serialized: bytes
    protected_headers: Mapping[int | str, object]
    unprotected_headers: Mapping[int | str, object]
    payload_or_ciphertext: bytes | None
    remaining: tuple[object, ...]
    tagged: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", CoseMessageKind(self.kind))
        object.__setattr__(self, "protected_headers", dict(self.protected_headers))
        object.__setattr__(self, "unprotected_headers", dict(self.unprotected_headers))
        object.__setattr__(self, "remaining", tuple(self.remaining))


def _decode_protected(value: bytes) -> Mapping[int | str, object]:
    if not isinstance(value, bytes):
        raise ValueError("COSE protected headers must be a byte string")
    if value == b"":
        return {}
    try:
        decoded = cbor2.loads(value)
    except (ValueError, TypeError) as exc:
        raise ValueError("invalid encoded COSE protected headers") from exc
    if not isinstance(decoded, Mapping):
        raise ValueError("COSE protected headers must encode a map")
    return dict(decoded)


def decode_cose_message(
    encoded: bytes,
    *,
    expected_kind: CoseMessageKind | str | None = None,
) -> CoseMessage:
    if not isinstance(encoded, bytes) or not encoded:
        raise ValueError("encoded COSE message is required")
    try:
        decoded = cbor2.loads(encoded)
    except (ValueError, TypeError) as exc:
        raise ValueError("invalid CBOR COSE message") from exc

    tagged = isinstance(decoded, cbor2.CBORTag)
    if tagged:
        try:
            kind = COSE_TAG_KINDS[decoded.tag]
        except KeyError as exc:
            raise ValueError(f"unsupported COSE tag: {decoded.tag}") from exc
        value = decoded.value
    else:
        if expected_kind is None:
            raise ValueError("untagged COSE messages require an expected kind")
        kind = CoseMessageKind(expected_kind)
        value = decoded

    if expected_kind is not None and kind is not CoseMessageKind(expected_kind):
        raise ValueError("COSE message kind does not match the expected kind")
    if not isinstance(value, (list, tuple)) or len(value) != _EXPECTED_LENGTHS[kind]:
        raise ValueError(f"{kind.value} has an invalid array shape")
    protected_serialized, unprotected, payload_or_ciphertext, *remaining = value
    if not isinstance(unprotected, Mapping):
        raise ValueError("COSE unprotected headers must be a map")
    if payload_or_ciphertext is not None and not isinstance(
        payload_or_ciphertext, bytes
    ):
        raise ValueError("COSE payload or ciphertext must be bytes or nil")

    return CoseMessage(
        kind=kind,
        encoded=encoded,
        protected_serialized=protected_serialized,
        protected_headers=_decode_protected(protected_serialized),
        unprotected_headers=dict(unprotected),
        payload_or_ciphertext=payload_or_ciphertext,
        remaining=tuple(remaining),
        tagged=tagged,
    )


__all__ = ["COSE_TAG_KINDS", "CoseMessage", "CoseMessageKind", "decode_cose_message"]
