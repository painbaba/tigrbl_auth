"""RFC 9711 claim-family composition and decoded claim-set schema."""

from dataclasses import dataclass
from tba_primitives_identity.enum_compat import StrEnum
from typing import Mapping

from tba_concrete_claim_eat_nonce import EatNonceClaim
from tba_concrete_claim_eat_profile import EatProfileClaim
from tba_concrete_claim_eat_submodules import EatSubmodulesClaim
from tba_concrete_claim_issued_at import IssuedAtClaim
from tba_concrete_claim_ueid import UeidClaim
from tba_contracts_identity.claims import ClaimSet

from .profiles import EatProfile
from .submodules import EatSubmodule, parse_submodules

EAT_CLAIM_CLASSES = (
    EatProfileClaim,
    EatNonceClaim,
    IssuedAtClaim,
    UeidClaim,
    EatSubmodulesClaim,
)


class EatEncoding(StrEnum):
    JSON = "json"
    CBOR = "cbor"


@dataclass(frozen=True, slots=True)
class EatClaimSetPayload:
    profile: EatProfile
    encoding: EatEncoding
    nonce: tuple[bytes | str, ...] = ()
    issued_at: int | None = None
    ueid: bytes | str | None = None
    submodules: tuple[EatSubmodule, ...] = ()
    raw_claims: Mapping[str | int, object] | None = None


def parse_eat_claims(
    claims: Mapping[str | int, object], encoding: EatEncoding
) -> EatClaimSetPayload:
    profile = claims.get("eat_profile", claims.get(265))
    nonce = claims.get("eat_nonce" if encoding is EatEncoding.JSON else 10)
    nonces = (
        () if nonce is None else tuple(nonce) if isinstance(nonce, list) else (nonce,)
    )
    issued_at = claims.get("iat", claims.get(6))
    if issued_at is not None and (
        not isinstance(issued_at, int) or isinstance(issued_at, bool)
    ):
        raise ValueError("EAT iat must be an integer NumericDate")
    ueid = claims.get("ueid", claims.get(256))
    if ueid is not None and not isinstance(ueid, (bytes, str)):
        raise ValueError("ueid must be a byte or text string")
    return EatClaimSetPayload(
        EatProfile(profile),
        encoding,
        nonces,
        issued_at,
        ueid,
        parse_submodules(claims.get("submods", claims.get(266))),
        dict(claims),
    )


def compose_eat_claim_set(*claims: object) -> ClaimSet:
    return ClaimSet(tuple(claims), "eat", "RFC9711")


__all__ = [
    "EAT_CLAIM_CLASSES",
    "EatClaimSetPayload",
    "EatEncoding",
    "compose_eat_claim_set",
    "parse_eat_claims",
]
