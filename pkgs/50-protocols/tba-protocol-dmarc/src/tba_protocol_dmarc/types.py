from dataclasses import dataclass
from enum import Enum


class PolicyStatus(str, Enum):
    FOUND = "found"
    MISSING = "missing"
    INVALID = "invalid"
    TEMPORARY_FAILURE = "temporary_failure"


@dataclass(frozen=True, slots=True)
class DmarcRecord:
    policy: str
    subdomain_policy: str | None = None
    nonexistent_policy: str | None = None
    testing: bool = False
    legacy_percentage: int = 100
    public_suffix: str = "u"


@dataclass(frozen=True, slots=True)
class PolicyDiscovery:
    status: PolicyStatus
    organizational_domain: str | None = None
    policy_source: str | None = None
    effective_policy: str | None = None
    record: DmarcRecord | None = None
    organizational_record: DmarcRecord | None = None
    reason: str | None = None
