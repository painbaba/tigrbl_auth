# tba-protocol-cwt

Owns RFC 8392 version history and composition of independently packaged integer-labelled CWT claims. It does not own CBOR/COSE cryptography or key resolution.

Draft `actx` and `ath` use text keys in `CWT_EXTENSION_CLAIMS`; both lookup maps
include these extensions without treating them as registered integer labels.
`build_cwt_claims(*claims, actx_field_labels=...)` builds a CBOR-ready
`CwtClaimsSet`, converting `actx` fields using explicit protocol labels and
`ath` to its 32-byte SHA-256 digest. This does not implement full DPoP verification.
