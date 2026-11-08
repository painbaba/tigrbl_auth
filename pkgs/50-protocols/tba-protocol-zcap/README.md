# tba-protocol-zcap

ZCAP-LD v0.4.0 delegation and HTTP invocation signing and verification for
the TBA Ed25519 development profile.

Use `ZcapRoot` to configure a trusted local root and `sign_delegation`
to grant a controller restricted actions at a target. A signed delegation
embeds its immediate delegated parent and references older ancestors by ID.
Use `sign_http_invocation` to present a root by ID or a leaf delegation as
gzip-compressed, base64url-encoded JSON.

Configure `ZcapVerifier` with a trusted local root lookup, an Ed25519 key
lookup, a revocation check, and a TBA replay reservation provider. The key
lookup takes the controller, verification method ID, and required proof
purpose. Return a key only if the method is authorized for that controller
and purpose. The revocation check takes the root and delegated capability IDs.
Supply the operation's trusted root, method, target, and action to
`verify_invocation`, then dispatch using the verified request.

Delegation proofs use `eddsa-jcs-2022`. The verifier hashes the canonical
proof options and the canonical unsigned document separately, then checks
the Ed25519 signature over their concatenated hashes. The two fixed
JSON-LD contexts are checked locally. This suite uses JSON canonicalization
and needs no remote context fetching or RDF canonicalization.

The HTTP profile uses one RFC 9421 signature named `zcap`. It signs the
method, full target URI, Capability-Invocation field, SHA-256 Content-Digest,
and Content-Type when present. The application supplies the externally
effective URL and unmodified body. Preserve repeated headers so the verifier
can reject duplicates. Each signature includes a creation time, an expiry,
and a nonce. Use shared atomic replay storage for a multi-worker deployment.

The profile accepts one controller per capability, explicit action
restrictions on delegations, simple HTTPS paths without query strings, and
up to eight delegated capabilities. It uses this exact Capability-Invocation
field syntax for root and delegated invocations, respectively.

```text
zcap id="<root-id>",action="read"
zcap capability=<base64url-gzip-json>,action="read"
```

This is a bounded profile. It does not implement JSON invocation proofs,
arbitrary JSON-LD contexts or caveats, query attenuation, or a revocation
endpoint.

- [ZCAP-LD v0.4.0](https://w3c-ccg.github.io/zcap-spec/v0.4.0/)
- [W3C EdDSA Data Integrity suites](https://www.w3.org/TR/vc-di-eddsa/#eddsa-jcs-2022)
- [RFC 9421 HTTP Message Signatures](https://www.rfc-editor.org/rfc/rfc9421.html)
- [RFC 9530 Digest Fields](https://www.rfc-editor.org/rfc/rfc9530.html)
