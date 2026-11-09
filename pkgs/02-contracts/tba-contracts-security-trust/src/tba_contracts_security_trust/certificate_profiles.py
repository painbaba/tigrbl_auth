from ._compat import StrEnum


class CertificateProfile(StrEnum):
    GENERIC_PKIX = "generic-pkix"
    OAUTH_MTLS = "oauth-mtls"
    X509_SVID = "x509-svid"
    MDOC_ISSUER = "mdoc-issuer"
    MDOC_READER = "mdoc-reader"
    HAIP_ISSUER = "haip-issuer"
    HAIP_VERIFIER = "haip-verifier"
    WALLET_ATTESTATION = "wallet-attestation"
    EAT_ENDORSEMENT = "eat-endorsement"
    BIMI_MARK = "bimi-mark"


__all__ = ["CertificateProfile"]
