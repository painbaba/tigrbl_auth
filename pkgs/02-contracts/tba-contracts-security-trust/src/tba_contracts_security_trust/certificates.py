from dataclasses import dataclass
from datetime import datetime
from typing import Sequence


@dataclass(frozen=True, slots=True)
class CertificateArtifact:
    der: bytes
    profile: str


@dataclass(frozen=True, slots=True)
class CertificatePathValidationRequest:
    leaf: CertificateArtifact
    intermediates: Sequence[bytes] = ()
    validation_time: datetime | None = None


@dataclass(frozen=True, slots=True)
class CertificatePathValidationResult:
    """A path decision. Indeterminate signals missing required trust evidence."""

    valid: bool
    profile: str
    trust_anchor_id: str | None = None
    errors: Sequence[str] = ()
    indeterminate: bool = False


__all__ = [
    "CertificateArtifact",
    "CertificatePathValidationRequest",
    "CertificatePathValidationResult",
]
