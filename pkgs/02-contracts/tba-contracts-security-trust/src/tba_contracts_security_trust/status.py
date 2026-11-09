from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from ._compat import StrEnum


class CertificateStatus(StrEnum):
    GOOD = "good"
    REVOKED = "revoked"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class CertificateStatusResult:
    status: CertificateStatus
    checked_at: datetime
    source: str


class CertificateStatusProviderPort(Protocol):
    def status(self, certificate_der: bytes, /) -> CertificateStatusResult: ...


__all__ = [
    "CertificateStatus",
    "CertificateStatusProviderPort",
    "CertificateStatusResult",
]
