from datetime import datetime
from hashlib import sha256

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from tba_contracts_security_trust import (
    CertificateArtifact,
    CertificatePathValidationRequest,
    CertificatePathValidatorPort,
    CertificateProfile,
)

from .logotype import verify_subject_logo
from .records import assertion_owner, normalize_domain, normalize_selector
from .types import CertificateOutcome, MarkType, MarkVerification

_MARK_TYPE = x509.ObjectIdentifier("1.3.6.1.4.1.53087.1.13")
_MARK_POLICY = x509.ObjectIdentifier("1.3.6.1.4.1.53087.1.1")
_BIMI_EKU = x509.ObjectIdentifier("1.3.6.1.5.5.7.3.31")
_LOGOTYPE = x509.ObjectIdentifier("1.3.6.1.5.5.7.1.12")
_TYPES = {
    "Registered Mark": MarkType.VMC,
    "Government Mark": MarkType.VMC,
    "Prior Use Mark": MarkType.CMC,
    "Modified Registered Mark": MarkType.CMC,
    "Provisional Mark": MarkType.CMC,
}
_MAX_PEM_BYTES = 512 * 1024
_MAX_CHAIN = 10


def _normalize_assertion(name: str) -> tuple[str, str]:
    selector, separator, domain = name.lower().partition("._bimi.")
    if not separator:
        raise ValueError("assertion name must be <selector>._bimi.<domain>")
    domain = normalize_domain(domain)
    return assertion_owner(normalize_selector(selector), domain), domain


def _matches_name(name: str, owner: str, domain: str) -> bool:
    try:
        if "._bimi." in name.lower():
            return _normalize_assertion(name)[0] == owner
        return normalize_domain(name) == domain
    except ValueError:
        return False


def _validate_leaf(leaf: x509.Certificate, owner: str, domain: str) -> MarkType:
    marks = leaf.subject.get_attributes_for_oid(_MARK_TYPE)
    if len(marks) != 1 or marks[0].value not in _TYPES:
        raise ValueError("unknown or ambiguous BIMI mark type")
    policies = leaf.extensions.get_extension_for_class(x509.CertificatePolicies).value
    if not any(policy.policy_identifier == _MARK_POLICY for policy in policies):
        raise ValueError("certificate is missing the Mark Certificate policy")
    eku = leaf.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
    if _BIMI_EKU not in eku:
        raise ValueError("certificate is missing the BIMI EKU")
    sans = leaf.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    if not any(
        _matches_name(name, owner, domain)
        for name in sans.get_values_for_type(x509.DNSName)
    ):
        raise ValueError("certificate SAN does not match the BIMI assertion name")
    logo = leaf.extensions.get_extension_for_oid(_LOGOTYPE).value
    if not isinstance(logo, x509.UnrecognizedExtension):
        raise ValueError("unsupported BIMI logotype representation")
    verify_subject_logo(logo.value)
    return _TYPES[marks[0].value]


def verify_certificate(
    pem: bytes,
    *,
    assertion_name: str,
    validator: CertificatePathValidatorPort,
    validation_time: datetime | None = None,
) -> MarkVerification:
    owner, domain = _normalize_assertion(assertion_name)
    if len(pem) > _MAX_PEM_BYTES:
        return MarkVerification(
            CertificateOutcome.INVALID, errors=("certificate bundle is too large",)
        )
    try:
        leaf, *chain = x509.load_pem_x509_certificates(pem)
        if len(chain) >= _MAX_CHAIN:
            raise ValueError("certificate bundle has too many certificates")
        der = leaf.public_bytes(serialization.Encoding.DER)
    except ValueError:
        return MarkVerification(
            CertificateOutcome.INVALID, errors=("invalid PEM certificate bundle",)
        )

    fingerprint = sha256(der).hexdigest()
    try:
        mark_type = _validate_leaf(leaf, owner, domain)
    except (ValueError, x509.ExtensionNotFound, x509.DuplicateExtension) as exc:
        return MarkVerification(
            CertificateOutcome.INVALID, sha256=fingerprint, errors=(str(exc),)
        )

    profile = CertificateProfile.BIMI_MARK
    result = validator.validate(
        CertificatePathValidationRequest(
            leaf=CertificateArtifact(der, profile),
            intermediates=tuple(
                cert.public_bytes(serialization.Encoding.DER) for cert in chain
            ),
            validation_time=validation_time,
        )
    )
    if result.profile != profile:
        return MarkVerification(
            CertificateOutcome.INVALID,
            mark_type,
            fingerprint,
            errors=("validator returned the wrong certificate profile",),
        )
    if result.indeterminate:
        outcome = CertificateOutcome.INDETERMINATE
    else:
        outcome = (
            CertificateOutcome.VALID if result.valid else CertificateOutcome.INVALID
        )
    return MarkVerification(
        outcome, mark_type, fingerprint, result.trust_anchor_id, tuple(result.errors)
    )
