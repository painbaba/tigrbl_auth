from dataclasses import dataclass
from tba_primitives_identity.enum_compat import StrEnum
from typing import Mapping, Protocol, Sequence


class EapAcrValue(StrEnum):
    PHISHING_RESISTANT = "phr"
    PHISHING_RESISTANT_HARDWARE = "phrh"


class EapAmrValue(StrEnum):
    PROOF_OF_POSSESSION = "pop"


@dataclass(frozen=True, slots=True)
class AuthenticatorEvidence:
    phishing_resistant: bool = False
    hardware_protected: bool = False
    user_verified: bool = False
    proof_of_possession: bool = False
    methods: Sequence[str] = ()
    properties: Mapping[str, object] | None = None


@dataclass(frozen=True, slots=True)
class EapAcrEvaluationRequest:
    requested: Sequence[EapAcrValue]
    evidence: Sequence[AuthenticatorEvidence]


@dataclass(frozen=True, slots=True)
class EapAcrEvaluationResult:
    achieved: tuple[EapAcrValue, ...]
    unmet: tuple[EapAcrValue, ...] = ()


class EapAcrEvaluatorPort(Protocol):
    def evaluate(
        self, request: EapAcrEvaluationRequest, /
    ) -> EapAcrEvaluationResult: ...


__all__ = [
    "AuthenticatorEvidence",
    "EapAcrEvaluationRequest",
    "EapAcrEvaluationResult",
    "EapAcrEvaluatorPort",
    "EapAcrValue",
    "EapAmrValue",
]
