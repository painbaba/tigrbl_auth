from tba_contracts_dns import TxtResolver
from tba_protocol_dmarc import PolicyStatus, discover_policy

from .types import CheckOutcome, DmarcCheck


def check_dmarc(
    dns: TxtResolver, domain: str, organizational_domain: str | None
) -> DmarcCheck:
    result = discover_policy(dns, domain, organizational_domain)
    if result.status is PolicyStatus.TEMPORARY_FAILURE:
        return DmarcCheck(
            CheckOutcome.INDETERMINATE,
            result.organizational_domain,
            result.policy_source,
            reason=result.reason,
        )
    if result.status is PolicyStatus.INVALID:
        return DmarcCheck(
            CheckOutcome.FAIL,
            result.organizational_domain,
            result.policy_source,
            reason=result.reason,
        )
    if result.organizational_record is None or result.record is None:
        return DmarcCheck(
            CheckOutcome.MISSING,
            result.organizational_domain,
            reason="an organizational DMARC policy is required",
        )

    outcome = CheckOutcome.PASS
    reason = None
    if any(
        record.policy == "none"
        or record.subdomain_policy == "none"
        or record.testing
        or record.legacy_percentage < 100
        for record in (result.organizational_record, result.record)
    ):
        outcome = CheckOutcome.FAIL
        reason = "BIMI requires full DMARC enforcement at the author and organizational domains"
    return DmarcCheck(
        outcome,
        result.organizational_domain,
        result.policy_source,
        result.effective_policy,
        reason,
    )
