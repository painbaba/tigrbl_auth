from collections.abc import Callable
from datetime import datetime

from cryptography import x509
from cryptography.exceptions import UnsupportedAlgorithm

CrlSource = Callable[[str], bytes | None]
_MAX_CRL_BYTES = 32 * 1024 * 1024


def load_crls(
    chain: list[x509.Certificate], source: CrlSource, at: datetime
) -> list[x509.CertificateRevocationList]:
    """Collect fresh, issuer-signed CRLs; OpenSSL subsequently checks their scope."""
    fetched: dict[str, bytes | None] = {}
    valid = []
    for certificate, issuer in zip(chain, chain[1:]):
        try:
            points = certificate.extensions.get_extension_for_class(
                x509.CRLDistributionPoints
            ).value
        except x509.ExtensionNotFound:
            continue
        for point in points:
            for location in point.full_name or ():
                if not isinstance(location, x509.UniformResourceIdentifier):
                    continue
                url = location.value
                if url not in fetched:
                    try:
                        fetched[url] = source(url)
                    except OSError:
                        fetched[url] = None
                crl = _load_crl(fetched[url], issuer, at)
                if crl is not None and crl not in valid:
                    valid.append(crl)
    return valid


def _load_crl(
    data: bytes | None, issuer: x509.Certificate, at: datetime
) -> x509.CertificateRevocationList | None:
    if not data or len(data) > _MAX_CRL_BYTES:
        return None
    try:
        if data.startswith(b"-----BEGIN X509 CRL-----"):
            crl = x509.load_pem_x509_crl(data)
        else:
            crl = x509.load_der_x509_crl(data)
        digest = crl.signature_hash_algorithm
        if (
            crl.issuer == issuer.subject
            and digest is not None
            and digest.name in {"sha256", "sha384", "sha512"}
            and crl.next_update_utc is not None
            and crl.last_update_utc <= at < crl.next_update_utc
            and crl.is_signature_valid(issuer.public_key())
        ):
            return crl
    except (ValueError, TypeError, UnsupportedAlgorithm):
        return None
    return None
