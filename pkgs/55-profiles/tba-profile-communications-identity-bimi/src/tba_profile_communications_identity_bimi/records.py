from tba_contracts_dns import (
    TxtResolver,
    normalize_domain,
    parse_tags,
    versioned_records,
)
from tba_protocol_bimi import AssertionStatus, assertion_owner, normalize_selector
from tba_protocol_bimi import discover_assertion as discover_bimi_assertion

from .types import AssertionCheck, CheckOutcome

_OUTCOMES = {
    AssertionStatus.FOUND: CheckOutcome.PASS,
    AssertionStatus.INVALID: CheckOutcome.FAIL,
    AssertionStatus.MISSING: CheckOutcome.MISSING,
    AssertionStatus.DECLINED: CheckOutcome.DECLINED,
    AssertionStatus.TEMPORARY_FAILURE: CheckOutcome.INDETERMINATE,
}


def discover_assertion(
    dns: TxtResolver, domain: str, selector: str, organizational_domain: str | None
) -> AssertionCheck:
    result = discover_bimi_assertion(dns, domain, selector, organizational_domain)
    return AssertionCheck(_OUTCOMES[result.status], result.assertion, result.reason)


__all__ = [
    "assertion_owner",
    "discover_assertion",
    "normalize_domain",
    "normalize_selector",
    "parse_tags",
    "versioned_records",
]
