from datetime import datetime

from tba_contracts_security_trust import CertificatePathValidatorPort
from tba_contracts_dns import TxtResolver

from .certificate import verify_certificate
from .readiness import check_readiness
from .types import (
    AssertionCheck,
    BimiAssertion,
    CertificateOutcome,
    CheckOutcome,
    DmarcCheck,
    MarkType,
    MarkVerification,
    ReadinessResult,
)


class BimiProfile:
    def __init__(self, *, dns: TxtResolver, validator: CertificatePathValidatorPort):
        self._dns = dns
        self._validator = validator

    def check_readiness(
        self,
        domain: str,
        *,
        selector: str = "default",
        organizational_domain: str | None = None,
    ) -> ReadinessResult:
        return check_readiness(
            domain,
            dns=self._dns,
            selector=selector,
            organizational_domain=organizational_domain,
        )

    def verify_certificate(
        self,
        pem: bytes,
        *,
        assertion_name: str,
        validation_time: datetime | None = None,
    ) -> MarkVerification:
        return verify_certificate(
            pem,
            assertion_name=assertion_name,
            validator=self._validator,
            validation_time=validation_time,
        )


__all__ = [
    "AssertionCheck",
    "BimiAssertion",
    "BimiProfile",
    "CertificateOutcome",
    "CheckOutcome",
    "DmarcCheck",
    "MarkType",
    "MarkVerification",
    "ReadinessResult",
    "check_readiness",
    "verify_certificate",
]
