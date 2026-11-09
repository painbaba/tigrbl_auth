"""Versioned JOSE artifact carrier descriptors."""

from dataclasses import dataclass
from tba_primitives_identity.enum_compat import StrEnum

from .errors import UnsupportedJoseMediaTypeError


class JoseArtifactKind(StrEnum):
    JOSE = "jose"
    JWS = "jws"
    JWE = "jwe"
    JWK = "jwk"
    JWKS = "jwks"


class JoseSerialization(StrEnum):
    COMPACT = "compact"
    JSON = "json"


@dataclass(frozen=True, slots=True)
class JoseCarrier:
    media_type: str
    artifact_kind: JoseArtifactKind
    serialization: JoseSerialization


JOSE_CARRIERS = (
    JoseCarrier("application/jose", JoseArtifactKind.JOSE, JoseSerialization.COMPACT),
    JoseCarrier("application/jose+json", JoseArtifactKind.JOSE, JoseSerialization.JSON),
    JoseCarrier("application/jwk+json", JoseArtifactKind.JWK, JoseSerialization.JSON),
    JoseCarrier(
        "application/jwk-set+json", JoseArtifactKind.JWKS, JoseSerialization.JSON
    ),
)


def select_carrier(media_type: str) -> JoseCarrier:
    for carrier in JOSE_CARRIERS:
        if carrier.media_type == media_type:
            return carrier
    raise UnsupportedJoseMediaTypeError(f"unsupported JOSE media type: {media_type}")


__all__ = [
    "JOSE_CARRIERS",
    "JoseArtifactKind",
    "JoseCarrier",
    "JoseSerialization",
    "select_carrier",
]
