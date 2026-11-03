# tba-concrete-claim-access-token-digest

Owns the standalone RFC 9449 `ath` claim object. Protocol packages compose it
into versioned claim sets; this package does not own DPoP request processing.

`to_cwt_value()` validates canonical base64url SHA-256 and returns 32 raw
bytes. `from_cwt_value()` converts the CBOR byte string back to the textual
claim. Existing textual claim construction remains compatible. CWT usage is
based on draft-nandakumar-moq-generic-dpop-proof-00; use text key `ath`
until a numeric label is assigned.
