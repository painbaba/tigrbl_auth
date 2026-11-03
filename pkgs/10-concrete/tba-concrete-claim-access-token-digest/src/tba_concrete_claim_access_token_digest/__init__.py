"""Standalone RFC 9449 access-token digest claim."""

import base64
import binascii

from tba_bases_claim import ClaimBase
from tba_primitives_identity import ClaimType, ClaimValueType


class AccessTokenDigestClaim(ClaimBase):
    claim_name = "ath"
    default_claim_type = ClaimType.AUTHENTICATION
    default_value_type = ClaimValueType.STRING
    default_standards = ("RFC9449",)

    @classmethod
    def validate_value(cls, value):
        if not isinstance(value, str) or not value:
            raise ValueError("ath must be a non-empty base64url digest")

    def to_cwt_value(self) -> bytes:
        """Return the raw SHA-256 digest used by draft CWT DPoP proofs."""
        try:
            encoded = self.value.encode("ascii")
            raw = base64.b64decode(encoded + b"=" * (-len(encoded) % 4),
                                   altchars=b"-_", validate=True)
        except (UnicodeEncodeError, binascii.Error, ValueError) as exc:
            raise ValueError("ath must be a base64url SHA-256 digest") from exc
        if len(raw) != 32 or base64.urlsafe_b64encode(raw).rstrip(b"=") != encoded:
            raise ValueError("ath must be a canonical base64url SHA-256 digest")
        return raw

    @classmethod
    def from_cwt_value(cls, value: bytes):
        if not isinstance(value, bytes) or len(value) != 32:
            raise ValueError("CWT ath must be a 32-byte SHA-256 digest")
        return cls(base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii"))


__all__ = ["AccessTokenDigestClaim"]
