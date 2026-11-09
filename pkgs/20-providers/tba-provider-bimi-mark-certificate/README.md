# tba-provider-bimi-mark-certificate

BIMI Mark Certificate path and evidence verification.

`MarkCertificatePathBackend` accepts an explicit set of RFC 6962 CT log public
keys in PEM format and a callable that supplies CRL bytes by distribution-point
URL. It validates the X.509 path against BIMI-scoped anchors, verifies signed
CRL coverage for the leaf and intermediates, and verifies at least one
embedded SCT against the configured keys. Callers configure which roots and
logs they trust and how they obtain fresh CRLs.

The provider delegates PKIX, CRL, and SCT verification to
`tba-provider-certificate-evidence`. This package applies the Mark Certificate
algorithm and EKU rules and scopes the permitted trust anchors.

Supply a TBA `TrustAnchorProviderPort` to use the backend directly as a
`CertificatePathValidatorPort`. To use existing
`ProfiledCertificatePathValidator` dispatch, register the callable backend
under `CertificateProfile.BIMI_MARK`. The dispatcher's leaf status provider is
an additional check in that composition. The backend performs its own
request-local evidence verification in both cases.

The backend uses supplied CRLs and performs no HTTP requests. A missing fresh
CRL or an unconfigured CT log can yield an indeterminate decision. The provider
doesn't use the system Web PKI trust store for Mark Certificates.
