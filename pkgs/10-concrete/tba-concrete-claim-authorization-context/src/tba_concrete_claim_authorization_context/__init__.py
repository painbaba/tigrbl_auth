"""Draft generic DPoP authorization context; no assigned numeric CWT label."""

from collections.abc import Mapping

from tba_bases_claim import ClaimBase
from tba_primitives_identity import ClaimType, ClaimValueType


class AuthorizationContextClaim(ClaimBase):
    claim_name = "actx"
    default_claim_type = ClaimType.AUTHORIZATION
    default_value_type = ClaimValueType.JSON_OBJECT
    default_standards = ("draft-nandakumar-moq-generic-dpop-proof-00",)

    @classmethod
    def validate_value(cls, value):
        if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
            raise ValueError("actx must be an object with string keys")
        if not isinstance(value.get("type"), str) or not value["type"]:
            raise ValueError("actx type must be a non-empty string")

    def to_cwt_value(self, *, field_labels=None):
        """Encode context fields using an explicit protocol-specific label map."""
        labels = dict(field_labels or {})
        if "type" in labels or 0 in labels.values():
            raise ValueError("actx key 0 is reserved for type")
        if any(not isinstance(k, str) or isinstance(v, bool) or not isinstance(v, int)
               for k, v in labels.items()) or len(set(labels.values())) != len(labels):
            raise ValueError("actx field labels must be unique integers")
        missing = set(self.value) - {"type"} - labels.keys()
        if missing:
            raise ValueError("actx protocol fields require explicit integer labels")
        return {0 if key == "type" else labels[key]: value
                for key, value in self.value.items()}


__all__ = ["AuthorizationContextClaim"]
