from tba_contracts_dns import (
    TxtResolver,
    TxtStatus,
    normalize_domain,
    versioned_records,
)

from .record import assertion_owner, normalize_selector, parse_assertion
from .types import AssertionDiscovery, AssertionStatus


def discover_assertion(
    dns: TxtResolver,
    domain: str,
    selector: str = "default",
    organizational_domain: str | None = None,
) -> AssertionDiscovery:
    """Find the selector's assertion at the author or organizational domain."""
    domain = normalize_domain(domain)
    selector = normalize_selector(selector)
    if organizational_domain is not None:
        organizational_domain = normalize_domain(organizational_domain)
        if domain != organizational_domain and not domain.endswith(
            "." + organizational_domain
        ):
            raise ValueError("organizational domain must contain the sending domain")
    domains = (domain,)
    if organizational_domain and organizational_domain != domain:
        domains += (organizational_domain,)
    for candidate in domains:
        name = assertion_owner(selector, candidate)
        answer = dns.lookup_txt(name)
        if answer.status is TxtStatus.TEMPORARY_FAILURE:
            return AssertionDiscovery(
                AssertionStatus.TEMPORARY_FAILURE, reason=f"DNS failure at {name}"
            )
        records = versioned_records(answer.records, b"BIMI1")
        if not records:
            continue
        if len(records) != 1:
            return AssertionDiscovery(
                AssertionStatus.INVALID, reason=f"multiple BIMI records at {name}"
            )
        try:
            assertion = parse_assertion(records[0], name=name)
        except ValueError as exc:
            return AssertionDiscovery(AssertionStatus.INVALID, reason=str(exc))
        if assertion.logo_url is None:
            return AssertionDiscovery(AssertionStatus.DECLINED, assertion)
        return AssertionDiscovery(AssertionStatus.FOUND, assertion)
    return AssertionDiscovery(AssertionStatus.MISSING)
