"""RFC 8392 integer-label mappings for canonical semantic claims."""

from dataclasses import dataclass
from typing import TypeAlias

from tba_concrete_cwt import CwtClaimsSet
from tba_concrete_claim_authorization_context import AuthorizationContextClaim
from tba_concrete_claim_access_token_digest import AccessTokenDigestClaim
from tba_concrete_claim_audience import AudienceClaim
from tba_bases_claim import ClaimBase
from tba_concrete_claim_expiration import ExpirationClaim
from tba_concrete_claim_issued_at import IssuedAtClaim
from tba_concrete_claim_issuer import IssuerClaim
from tba_concrete_claim_jwt_id import JwtIdClaim
from tba_concrete_claim_not_before import NotBeforeClaim
from tba_concrete_claim_subject import SubjectClaim
from tba_contracts_identity.claims import ClaimSet

from .versions import CURRENT_VERSION, CwtVersion


ClaimClass: TypeAlias = type[ClaimBase]


@dataclass(frozen=True, slots=True)
class CwtClaimBinding:
    label: str | int
    claim_class: ClaimClass

    @property
    def semantic_name(self) -> str:
        return str(self.claim_class.claim_name)


CWT_REGISTERED_CLAIMS = (
    CwtClaimBinding(1, IssuerClaim),
    CwtClaimBinding(2, SubjectClaim),
    CwtClaimBinding(3, AudienceClaim),
    CwtClaimBinding(4, ExpirationClaim),
    CwtClaimBinding(5, NotBeforeClaim),
    CwtClaimBinding(6, IssuedAtClaim),
    CwtClaimBinding(7, JwtIdClaim),
)
# Draft extensions have no assigned integer labels; never invent IANA values.
CWT_EXTENSION_CLAIMS = (
    CwtClaimBinding("actx", AuthorizationContextClaim),
    CwtClaimBinding("ath", AccessTokenDigestClaim),
)
CWT_LABEL_BY_CLAIM = {
    binding.claim_class: binding.label for binding in (*CWT_REGISTERED_CLAIMS, *CWT_EXTENSION_CLAIMS)
}
CWT_CLAIM_BY_LABEL = {
    binding.label: binding.claim_class for binding in (*CWT_REGISTERED_CLAIMS, *CWT_EXTENSION_CLAIMS)
}


def compose_cwt_claim_set(
    *claims: ClaimBase,
    version: CwtVersion = CURRENT_VERSION,
) -> ClaimSet:
    return ClaimSet(tuple(claims), "cwt", version.value)


def cwt_label_for(claim: ClaimBase | ClaimClass) -> str | int:
    claim_class = claim if isinstance(claim, type) else type(claim)
    try:
        return CWT_LABEL_BY_CLAIM[claim_class]
    except KeyError as exc:
        raise ValueError(
            f"claim is not registered by CWT: {claim_class.__name__}"
        ) from exc


def build_cwt_claims(*claims: ClaimBase, actx_field_labels=None) -> CwtClaimsSet:
    """Map semantic objects to CWT keys and carrier-specific values."""
    values = {}
    for claim in claims:
        label = cwt_label_for(claim)
        if label in values:
            raise ValueError(f"duplicate CWT claim: {label}")
        if isinstance(claim, AuthorizationContextClaim):
            value = claim.to_cwt_value(field_labels=actx_field_labels)
        elif isinstance(claim, AccessTokenDigestClaim):
            value = claim.to_cwt_value()
        else:
            value = claim.value
        values[label] = value
    return CwtClaimsSet(values)


__all__ = [
    "CWT_CLAIM_BY_LABEL",
    "CWT_EXTENSION_CLAIMS",
    "build_cwt_claims",
    "CWT_LABEL_BY_CLAIM",
    "CWT_REGISTERED_CLAIMS",
    "CwtClaimBinding",
    "compose_cwt_claim_set",
    "cwt_label_for",
]
