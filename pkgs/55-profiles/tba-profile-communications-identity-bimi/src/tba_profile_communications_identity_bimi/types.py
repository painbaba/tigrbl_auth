from dataclasses import dataclass
from enum import Enum

from tba_protocol_bimi import BimiAssertion


class CheckOutcome(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    MISSING = "missing"
    DECLINED = "declined"
    INDETERMINATE = "indeterminate"


class CertificateOutcome(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    INDETERMINATE = "indeterminate"


class MarkType(str, Enum):
    CMC = "cmc"
    VMC = "vmc"


@dataclass(frozen=True, slots=True)
class AssertionCheck:
    outcome: CheckOutcome
    assertion: BimiAssertion | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class DmarcCheck:
    outcome: CheckOutcome
    organizational_domain: str | None = None
    policy_source: str | None = None
    effective_policy: str | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ReadinessResult:
    domain: str
    selector: str
    bimi: AssertionCheck
    dmarc: DmarcCheck

    @property
    def assertion_name(self) -> str | None:
        return self.bimi.assertion.name if self.bimi.assertion else None

    @property
    def ready(self) -> bool:
        assertion = self.bimi.assertion
        return (
            self.dmarc.outcome is CheckOutcome.PASS
            and self.bimi.outcome is CheckOutcome.PASS
            and assertion is not None
            and assertion.evidence_url is not None
        )


@dataclass(frozen=True, slots=True)
class MarkVerification:
    outcome: CertificateOutcome
    mark_type: MarkType | None = None
    sha256: str | None = None
    trust_anchor_id: str | None = None
    errors: tuple[str, ...] = ()
