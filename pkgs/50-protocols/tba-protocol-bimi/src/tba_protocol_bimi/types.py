from dataclasses import dataclass
from enum import Enum


class AssertionStatus(str, Enum):
    FOUND = "found"
    INVALID = "invalid"
    MISSING = "missing"
    DECLINED = "declined"
    TEMPORARY_FAILURE = "temporary_failure"


@dataclass(frozen=True, slots=True)
class BimiAssertion:
    name: str
    logo_url: str | None
    evidence_url: str | None


@dataclass(frozen=True, slots=True)
class AssertionDiscovery:
    status: AssertionStatus
    assertion: BimiAssertion | None = None
    reason: str | None = None
