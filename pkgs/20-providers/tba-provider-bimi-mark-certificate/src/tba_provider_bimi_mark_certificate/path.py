from collections.abc import Iterable, Sequence
from datetime import datetime, timezone

from cryptography import x509
from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from tba_contracts_security_trust import (
    CertificatePathValidationRequest,
    CertificatePathValidationResult,
    CertificateProfile,
    TrustAnchor,
    TrustAnchorProviderPort,
)

from tba_provider_certificate_evidence import (
    CrlSource,
    CtEvidenceUnavailable,
    PathValidationError,
    load_crls,
    load_logs,
    verify_chain,
    verify_transparency,
)

_PROFILE = CertificateProfile.BIMI_MARK
_BIMI_EKU = x509.ObjectIdentifier("1.3.6.1.5.5.7.3.31")
_MAX_CHAIN = 10
_MAX_CERT_BYTES = 256 * 1024
_ALLOWED_HASHES = {"sha256", "sha384", "sha512"}


def _check_bimi_chain(chain: list[x509.Certificate]) -> None:
    for cert in chain:
        key = cert.public_key()
        if not (
            (isinstance(key, rsa.RSAPublicKey) and key.key_size >= 2048)
            or (
                isinstance(key, ec.EllipticCurvePublicKey)
                and key.curve.name
                in {
                    "secp256r1",
                    "secp384r1",
                    "secp521r1",
                }
            )
        ):
            raise ValueError("certificate path uses an unsupported public key")
    for cert in chain[:-1]:
        if (
            cert.signature_hash_algorithm is None
            or cert.signature_hash_algorithm.name not in _ALLOWED_HASHES
        ):
            raise ValueError("certificate path uses an unsupported signature hash")
        try:
            eku = cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
        except x509.ExtensionNotFound as exc:
            raise ValueError("certificate path is missing the BIMI EKU") from exc
        if _BIMI_EKU not in eku:
            raise ValueError("certificate path is missing the BIMI EKU")
    try:
        constraints = (
            chain[0].extensions.get_extension_for_class(x509.BasicConstraints).value
        )
    except x509.ExtensionNotFound:
        return  # Basic Constraints is optional on a BIMI subscriber certificate.
    if constraints.ca:
        raise ValueError("BIMI subscriber certificate cannot be a CA")


class MarkCertificatePathBackend:
    """BIMI path backend with a request-local trust and evidence check.

    Supply a TBA anchor provider to also use the backend as a validator port.
    """

    def __init__(
        self,
        *,
        crl_source: CrlSource,
        ct_logs: Iterable[bytes],
        anchors: TrustAnchorProviderPort | None = None,
    ) -> None:
        self._crl_source = crl_source
        self._logs = load_logs(ct_logs)
        self._anchors = anchors

    def validate(
        self, request: CertificatePathValidationRequest, /
    ) -> CertificatePathValidationResult:
        if self._anchors is None:
            raise ValueError("configure an anchor provider to call validate directly")
        return self(request, self._anchors.anchors_for(_PROFILE))

    def __call__(
        self, request: CertificatePathValidationRequest, anchors: Sequence[TrustAnchor]
    ) -> CertificatePathValidationResult:
        def failure(
            reason: str, *, indeterminate: bool = False
        ) -> CertificatePathValidationResult:
            return CertificatePathValidationResult(
                False,
                request.leaf.profile,
                errors=(reason,),
                indeterminate=indeterminate,
            )

        if request.leaf.profile != _PROFILE:
            return failure("unsupported certificate profile")
        at = request.validation_time or datetime.now(timezone.utc)
        if at.tzinfo is None or at.utcoffset() is None:
            raise ValueError("validation time must be timezone-aware")
        at = at.astimezone(timezone.utc)
        trusted = {
            anchor.certificate_der: anchor.identifier
            for anchor in anchors
            if _PROFILE in anchor.profiles
        }
        if not trusted:
            return failure("no BIMI trust anchors configured", indeterminate=True)
        supplied = (request.leaf.der, *request.intermediates)
        if len(supplied) > _MAX_CHAIN or any(
            len(der) > _MAX_CERT_BYTES for der in supplied
        ):
            return failure("BIMI certificate chain exceeds size limits")

        try:
            leaf, *intermediates = [
                x509.load_der_x509_certificate(der) for der in supplied
            ]
            roots = [x509.load_der_x509_certificate(der) for der in trusted]
            chain = verify_chain(leaf, intermediates, roots, at)
            if len(chain) < 2:
                return failure("a BIMI subscriber certificate cannot be a trust anchor")
        except (
            ValueError,
            x509.DuplicateExtension,
        ):
            return failure("BIMI certificate path validation failed")
        try:
            _check_bimi_chain(chain)
        except (ValueError, UnsupportedAlgorithm, x509.DuplicateExtension) as exc:
            return failure(str(exc))

        try:
            crls = load_crls(chain, self._crl_source, at)
            verify_chain(leaf, chain[1:-1], chain[-1:], at, crls)
        except PathValidationError as exc:
            if exc.revoked:
                return failure("certificate path contains a revoked certificate")
            return failure(
                "fresh CRL coverage is unavailable for the certificate path",
                indeterminate=True,
            )
        except (ValueError, x509.DuplicateExtension):
            return failure("invalid revocation evidence for the certificate path")

        try:
            verify_transparency(chain[0], chain[1], self._logs, at)
        except CtEvidenceUnavailable as exc:
            return failure(str(exc), indeterminate=True)
        except (ValueError, x509.DuplicateExtension) as exc:
            return failure(f"invalid CT evidence: {exc}")

        anchor_der = chain[-1].public_bytes(serialization.Encoding.DER)
        return CertificatePathValidationResult(True, _PROFILE, trusted[anchor_der])
