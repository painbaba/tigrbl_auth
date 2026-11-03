"""Deterministic RFC 8392 CWT claim-set values."""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

import cbor2

CWT_CLAIM_LABELS = MappingProxyType(
    {"iss": 1, "sub": 2, "aud": 3, "exp": 4, "nbf": 5, "iat": 6, "cti": 7, "cnf": 8,
     "actx": "actx", "ath": "ath"}
)


@dataclass(frozen=True, slots=True)
class CwtClaimsSet:
    claims: Mapping[str | int, object]

    def __post_init__(self) -> None:
        normalized = dict(self.claims)
        if not normalized:
            raise ValueError("CWT claims set must not be empty")
        if not all(
            not isinstance(label, bool) and isinstance(label, (str, int))
            for label in normalized
        ):
            raise ValueError("CWT claim labels must be text strings or integers")
        object.__setattr__(self, "claims", MappingProxyType(normalized))

    # Draft extension names retain text keys until numeric labels are assigned.
    def get_registered(self, name: str, default: object = None) -> object:
        label = CWT_CLAIM_LABELS[name]
        return self.claims.get(label, self.claims.get(name, default))

    def encode(self) -> bytes:
        return cbor2.dumps(dict(self.claims), canonical=True)


def decode_cwt_claims(encoded: bytes) -> CwtClaimsSet:
    if not isinstance(encoded, bytes) or not encoded:
        raise ValueError("encoded CWT claims are required")
    try:
        value = cbor2.loads(encoded)
    except (ValueError, TypeError) as exc:
        raise ValueError("invalid CBOR CWT claims set") from exc
    if not isinstance(value, Mapping):
        raise ValueError("CWT claims set must be a CBOR map")
    return CwtClaimsSet(value)
