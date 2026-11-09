"""Canonical DID verification-method contracts."""

from dataclasses import dataclass
from tba_primitives_identity.enum_compat import StrEnum
from typing import Mapping

from .identifiers import Did


class VerificationRelationship(StrEnum):
    AUTHENTICATION = "authentication"
    ASSERTION_METHOD = "assertionMethod"
    KEY_AGREEMENT = "keyAgreement"
    CAPABILITY_INVOCATION = "capabilityInvocation"
    CAPABILITY_DELEGATION = "capabilityDelegation"


@dataclass(frozen=True, slots=True)
class DidVerificationMethod:
    identifier: str
    controller: Did
    method_type: str
    public_key: Mapping[str, object]


__all__ = ["DidVerificationMethod", "VerificationRelationship"]
