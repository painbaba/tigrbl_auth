# tba_auth Package Graph Brief

This brief grounds the architecture image in the live package inventory in this checkout.

## Package inventory

### Runtime and compatibility shell

- `tba-auth`: compatibility facade preserving legacy `app`, `gateway`, `plugin`, CLI, and RFC import paths over the split package suite.
- `tba-server-identity`: ASGI composition layer that builds public REST and admin RPC surfaces.
- `tba-runtime-identity`: runtime planning, profile resolution, feature flags, deployment resolution, and runner adapters.
- `tba-operator-identity`: operator CLI, repo truth, evidence workflows, and admin console helpers.

### Domain, protocol, and control-plane packages

- `tba-runtime-identity-administration`: tenant, user, client, key, session, token, consent, audit, profile, and governance control-plane operations.
- `tba-protocol-oauth`: OAuth 2.x protocol flows including device authorization, PAR, token exchange, DPoP, and related RFC helpers.
- `tba-protocol-oidc`: OIDC discovery, ID token, userinfo, logout, session, and OIDC standards helpers.
- `tba-credentials`: password, API key, auth context, session, and token lifecycle helpers.
- `tba-runtime-authorization-policy`: RBAC, ABAC, delegated administration, provenance, and governance policy controls.
- `tba-concrete-identity-principals`: tenant, principal, subject context, and trust-domain discovery helpers.
- `tba-provider-identity-jose`: JOSE, JWT, JWS, JWE, JWK, JWKS, key rotation, and signing helpers.
- `tba-contracts-identity`: Pydantic REST and JSON-RPC contracts for public and admin APIs.

### Foundation and persistence packages

- `tba-storage-core`: SQLAlchemy tables, ORM models, migrations, persistence helpers, and operator state storage.
- `tba-primitives-identity` owns shared identity helpers and the deterministic JSON used for existing hashes. Its strict JCS exports are deprecated compatibility entry points.
- `tba-codec-jcs` owns RFC 8785 canonicalization and its conformance tests. Import `canonicalize` and `canonicalize_json` from `tba_codec_jcs`.

### Consumer and verification packages

- `tba-protocol-oidc-relying-party`: Python relying-party helpers for discovery, userinfo, logout, and RP integration.
- `tba-protocol-oauth-protected-resource`: protected API token-validation and resource-server contracts.
- `tba-testkit-identity`: fake identity components, vectors, fixtures, and integration harnesses.
- `acme-notes-cli`: example consumer showing device-login usage.

### UI and browser packages

- `@tba/ui-public`: public end-user UI built against generated OpenAPI and OIDC discovery surfaces.
- `@tba/ui-administration`: admin UI built against generated OpenRPC admin/control-plane surfaces.
- `@tba/client-oidc-relying-party`: browser-safe TypeScript relying-party SDK.

## Production block model

### Edge and consumer block

- Public UI, admin UI, browser RP SDK, Python RP helpers, resource-server helpers, and the example CLI live at the edge of production systems.
- These packages either call public REST and OIDC discovery endpoints or the admin RPC/OpenRPC surface.

### Runtime composition block

- `tba-server-identity` is the main composition package for the running identity provider.
- `tba-runtime-identity` resolves profiles, surfaces, flags, deployment style, and runner choice before the server is started.
- `tba-auth` remains the compatibility shell that preserves older import and entrypoint paths across the split architecture.

### Domain services block

- OAuth, OIDC, admin, credential, policy, principal, JOSE, and contract packages provide the operational logic and protocol surface definitions used by the server.
- The operator package sits adjacent to this block because it uses the same runtime truth to generate evidence, surface reports, and installation artifacts.

### Data and foundation block

- Storage anchors persistence, migrations, and the state tables consumed by the runtime.
- Core provides low-level primitives and helper types that support the rest of the graph.

### Verification and governance sidecar block

- Testkit validates cross-cutting flows, conformance vectors, and fake peers.
- Operator workflows and SSOT artifacts support release governance and certification evidence.

## High-level flow edges

1. Public users and consumer apps enter through `@tba/ui-public`, `@tba/client-oidc-relying-party`, `tba-protocol-oidc-relying-party`, or the example CLI.
2. Administrative operators enter through `@tba/ui-administration` and `tba-operator-identity`.
3. Those clients call the `tba-server-identity` public REST or admin RPC surfaces.
4. The server delegates protocol and domain work to OAuth, OIDC, admin, credentials, policy, principals, JOSE, and contracts packages.
5. Domain logic persists and reads state through `tba-storage-core`.
6. Runtime startup and deployment behavior are resolved by `tba-runtime-identity`.
7. Legacy consumers can still enter through `tba-auth`, which forwards to the split runtime and server entrypoints.
