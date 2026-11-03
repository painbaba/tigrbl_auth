# Authorization context claim

`AuthorizationContextClaim` owns the draft `actx` object, including its required
non-empty `type`. This is distinct from the OIDC `acr` assurance-class string.
`to_cwt_value(field_labels=...)` produces a CBOR-ready map with type at key 0;
protocol fields require explicit labels. Protocol-specific authorization remains
the caller's responsibility. Use the text claim key `actx` until a numeric label
is assigned; this package does not claim IANA registration or full DPoP support.

Reference: https://www.ietf.org/archive/id/draft-nandakumar-moq-generic-dpop-proof-00.html
