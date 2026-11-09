from tba_contracts_dns import TxtResolver

from .dmarc import check_dmarc
from .records import (
    assertion_owner,
    discover_assertion,
    normalize_domain,
    normalize_selector,
)
from .types import ReadinessResult


def check_readiness(
    domain: str,
    *,
    dns: TxtResolver,
    selector: str = "default",
    organizational_domain: str | None = None,
) -> ReadinessResult:
    domain = normalize_domain(domain)
    selector = normalize_selector(selector)
    assertion_owner(selector, domain)
    dmarc = check_dmarc(dns, domain, organizational_domain)
    bimi = discover_assertion(dns, domain, selector, dmarc.organizational_domain)
    return ReadinessResult(domain, selector, bimi, dmarc)
