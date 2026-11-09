from collections.abc import Callable

from tba_capability_communications_identity import DomainCheck, DomainOutcome

from . import BimiProfile
from .types import BimiAssertion, CertificateOutcome, CheckOutcome


class BimiDomainChecker:
    """Adapt BIMI to the shared domain assessment workflow."""

    profile = "bimi"

    def __init__(
        self,
        bimi: BimiProfile,
        *,
        evidence: Callable[[BimiAssertion], bytes | None],
        selector: str = "default",
        organizational_domain: str | None = None,
    ) -> None:
        self._bimi = bimi
        self._evidence = evidence
        self._selector = selector
        self._organizational_domain = organizational_domain

    def check(self, domain: str, /) -> DomainCheck:
        readiness = self._bimi.check_readiness(
            domain,
            selector=self._selector,
            organizational_domain=self._organizational_domain,
        )
        assertion = readiness.bimi.assertion
        details = {
            "assertion": readiness.assertion_name,
            "bimi": readiness.bimi.outcome.value,
            "dmarc": readiness.dmarc.outcome.value,
        }
        if CheckOutcome.INDETERMINATE in (
            readiness.bimi.outcome,
            readiness.dmarc.outcome,
        ):
            return DomainCheck(readiness.domain, DomainOutcome.INDETERMINATE, details)
        if not readiness.ready or assertion is None:
            return DomainCheck(readiness.domain, DomainOutcome.NOT_READY, details)
        try:
            pem = self._evidence(assertion)
        except OSError:
            pem = None
        if pem is None:
            details["certificate"] = "unavailable"
            return DomainCheck(readiness.domain, DomainOutcome.INDETERMINATE, details)
        result = self._bimi.verify_certificate(pem, assertion_name=assertion.name)
        details.update(
            certificate=result.outcome.value,
            certificate_sha256=result.sha256,
            mark_type=result.mark_type.value if result.mark_type else None,
        )
        outcome = {
            CertificateOutcome.VALID: DomainOutcome.READY,
            CertificateOutcome.INVALID: DomainOutcome.NOT_READY,
            CertificateOutcome.INDETERMINATE: DomainOutcome.INDETERMINATE,
        }[result.outcome]
        return DomainCheck(readiness.domain, outcome, details)
