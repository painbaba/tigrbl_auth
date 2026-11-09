from collections.abc import Sequence
from datetime import datetime, timezone

from cryptography import x509
from OpenSSL import crypto

_CERT_REVOKED = 23  # OpenSSL X509_V_ERR_CERT_REVOKED.


class PathValidationError(ValueError):
    def __init__(self, message: str, *, revoked: bool):
        super().__init__(message)
        self.revoked = revoked


def verify_chain(
    leaf: x509.Certificate,
    intermediates: Sequence[x509.Certificate],
    anchors: Sequence[x509.Certificate],
    at: datetime,
    crls: Sequence[x509.CertificateRevocationList] | None = None,
) -> list[x509.Certificate]:
    """Build a path using only supplied anchors and optional CRL evidence."""
    if at.utcoffset() is None:
        raise ValueError("validation time must be timezone-aware")
    try:
        store = crypto.X509Store()
        store.set_time(at.astimezone(timezone.utc))
        flags = (
            crypto.X509StoreFlags.X509_STRICT | crypto.X509StoreFlags.CHECK_SS_SIGNATURE
        )
        if crls is not None:
            flags |= (
                crypto.X509StoreFlags.CRL_CHECK | crypto.X509StoreFlags.CRL_CHECK_ALL
            )
            for crl in crls:
                store.add_crl(crl)
        store.set_flags(flags)
        for anchor in anchors:
            store.add_cert(crypto.X509.from_cryptography(anchor))
        context = crypto.X509StoreContext(
            store,
            crypto.X509.from_cryptography(leaf),
            [crypto.X509.from_cryptography(cert) for cert in intermediates],
        )
        return [cert.to_cryptography() for cert in context.get_verified_chain()]
    except crypto.X509StoreContextError as exc:
        raise PathValidationError(
            str(exc), revoked=exc.errors[0] == _CERT_REVOKED
        ) from exc
    except crypto.Error as exc:
        raise ValueError("invalid certificate store inputs") from exc
