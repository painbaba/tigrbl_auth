# Authenticator Lifecycle API + Authenticator Center UIX Requirements Brief

**Proposed pairing:** `tba-router-authenticators` + `@tba/ui-authenticator-center-uix`<br>
**Status:** New product surface; existing provider and contract foundations<br>
**Prepared:** July 11, 2026<br>
**Proposed router owner:** `pkgs/80-routers/tba-router-authenticators`<br>
**Proposed UIX owner:** `pkgs/105-ui/authenticator-center-uix`

## 1. Product Decision

Create a dedicated authenticator lifecycle surface that owns enrollment, verification, naming, activation, suspension, replacement, recovery, revocation, and assurance evidence for human authenticators.

The API should compose existing authenticator providers rather than reimplement password, OTP, WebAuthn, federation, mTLS, DPoP, session, API-key, client-secret, or service-key verification. The UIX should expose two explicitly authorized modes:

- **My Authenticators:** current-subject enrollment and recovery.
- **Tenant Authenticator Administration:** tenant policy, help-desk lifecycle, and constrained administrative actions.

Workload/API/client credential lifecycle remains owned by Service Admin, Developer, Workload Trust, and Certificate Operations. The authenticator catalog may describe those provider types, but this UIX must not become another universal credential console.

## 2. Why This Pairing Is Needed

The repository already has:

- `tba-bases-identity-authenticator` and challenge-authenticator contracts;
- password, OTP, recovery-code, WebAuthn, federated OIDC, session, remote introspection, API-key, client-secret, service-key, mTLS certificate, and DPoP proof providers;
- authenticator metadata with kind, AMR values, properties, and challenge ceremonies;
- ACR and AMR evaluator providers;
- credential lifecycle contracts and concrete credential variants;
- advanced identity models for MFA factors and WebAuthn credentials;
- public UIX MFA and My Account security entry points.

What is missing is a single durable lifecycle authority. SSOT also shows absent/planned work for canonical authentication-context vocabulary, achieved versus required context, credential-use decisions, several passkey/WebAuthn identity models, account-owned storage operations, and credential binding lifecycle.

Without this pairing, authenticator features risk appearing in login UI before enrollment, recovery, policy, revocation, and evidence semantics are complete.

## 3. Users and Jobs

### End user

1. See which sign-in methods are registered.
2. Add and verify a passkey, OTP method, or recovery method.
3. Name devices/authenticators and recognize their provenance.
4. Replace or remove a method safely.
5. Generate, acknowledge, rotate, and consume recovery codes.
6. Recover when a primary authenticator is unavailable.

### Tenant administrator or help desk

1. Define allowed/required authenticator classes and enrollment policy.
2. See enrollment state and safe metadata without secret material.
3. Require re-enrollment, suspend a compromised authenticator, or initiate approved recovery.
4. Understand whether actions would lock out the user.
5. Review authenticator lifecycle and recovery audit events.

### Security and identity engineer

1. Map authenticators to AMR, ACR/AAL, phishing-resistance, user-presence, user-verification, verifier-name binding, sender constraint, and replay resistance.
2. Configure step-up eligibility and high-risk action requirements.
3. Validate attestation, origin/RP ID, algorithms, counters, and provider health.
4. Test positive and negative ceremonies without exposing real credentials.

## 4. API Boundary

### Proposed current-subject routes

- `GET /account/authenticators`
- `GET /account/authenticators/catalog`
- `POST /account/authenticators/{kind}/enroll/start`
- `POST /account/authenticators/{kind}/enroll/finish`
- `PATCH /account/authenticators/{id}` for safe metadata such as display name
- `POST /account/authenticators/{id}/verify/start`
- `POST /account/authenticators/{id}/verify/finish`
- `POST /account/authenticators/{id}/replace/start`
- `DELETE /account/authenticators/{id}`
- `POST /account/recovery-codes/rotate`
- `GET /account/authentication-context`

### Proposed tenant-admin routes

- `GET /admin/authenticators/policy`
- `PATCH /admin/authenticators/policy`
- `GET /admin/identities/{identity_id}/authenticators`
- `POST /admin/identities/{identity_id}/authenticators/{id}/suspend`
- `POST /admin/identities/{identity_id}/authenticators/{id}/require-reenrollment`
- `POST /admin/identities/{identity_id}/recovery/start`
- `GET /admin/authenticators/audit`

Route names are proposed contracts, not authorization shortcuts. Every administrative operation requires tenant filtering, effective permission, purpose, audit, and self-lockout protection.

### Provider catalog

The API may expose metadata for:

- password;
- TOTP/HOTP or separately named OTP modes;
- recovery code;
- WebAuthn/passkey;
- federated OIDC authenticator;
- session authenticator;
- mTLS client certificate and DPoP proof where applicable to human/device-bound flows;
- remote introspection as a verification dependency.

API keys, client secrets, and service keys must link to their owning product surfaces rather than becoming user authenticators.

### Prohibited access

The API/UIX must fail closed on:

- tenant lifecycle and cross-tenant administration;
- OAuth client and service identity credential CRUD;
- raw private keys, passkey private material, OTP seeds after enrollment, passwords, recovery-code hashes, cookies, or bearer tokens;
- arbitrary attestation or certificate issuance;
- policy decisions outside authentication-method eligibility/context;
- direct mutation of provider registries from a browser.

## 5. Canonical Domain Model

### Authenticator

Minimum fields:

- immutable ID;
- principal/subject and tenant ownership;
- provider/kind;
- display name;
- lifecycle state: pending, active, suspended, compromised, replacement-pending, revoked, expired;
- enrolled, last verified, last used, expires, suspended, revoked timestamps;
- AMR values and achieved properties;
- credential binding and device/provider metadata;
- attestation summary and provenance where relevant;
- recovery eligibility;
- audit correlation and version.

### Authenticator properties

Use registry-backed vocabulary. At minimum distinguish:

- user present;
- user verified;
- phishing resistant;
- verifier-name bound;
- replay resistant;
- sender constrained;
- hardware backed;
- synced versus device bound;
- discoverable credential;
- resident/non-resident where relevant;
- attested versus unverified provenance.

Do not encode “phishing resistant” as an AAL value. Required ACR/AAL, AMR methods, and properties must remain separate concepts, matching the repository’s planned authentication-context contracts.

### Ceremony

Challenge ceremonies require:

- opaque short-lived transaction ID;
- kind and operation;
- subject/tenant binding;
- challenge and expiry;
- origin/RP/audience binding;
- attempt/replay state;
- required user presence/verification;
- safe result and reason code;
- correlation ID.

No ceremony may be completed for a different subject, origin, tenant, or operation.

## 6. Authenticator-Specific Requirements

### Password

- Support change, reset, forced change, compromise response, and passwordless-policy interaction.
- Never reveal password hashes or policy internals that aid guessing.
- Do not treat password presence alone as strong assurance.
- Support password managers and paste.

### OTP

- Name TOTP and HOTP precisely; do not use generic “MFA code” when behavior differs.
- Show QR/secret once during enrollment, then verify before activation.
- Never expose the seed after activation.
- Protect against replay, excessive retries, clock drift abuse, and unsafe reset.

### Recovery codes

- Generate server-side, show once, require acknowledgment, store only protected representations, and invalidate prior sets on rotation.
- Display remaining count, not code values.
- Treat use as a recovery event that may require re-enrollment or security review.

### WebAuthn and passkeys

- Support registration and authentication ceremonies with correct RP ID, origin, challenge, user verification, algorithm, counter, and credential binding checks.
- Distinguish synced and device-bound passkeys only when evidence supports the classification.
- Show provider/device hints conservatively; never claim exact device ownership from unreliable user-agent metadata.
- Support attestation policy modes: none, indirect/anonymized, direct/enterprise only where justified.
- Provide discoverable credential/usernameless readiness and backup-state signals without overclaiming hardware protection.

### Federated OIDC

- Model a federated account binding as an authenticator relationship, separate from the upstream provider registry.
- Show provider, upstream subject pairwise/safe identifier, linked time, last use, and status.
- Require recent authentication before linking/unlinking and protect against account-linking takeover.

### mTLS and DPoP

- Treat these primarily as proof-of-possession/binding mechanisms, not generic MFA factors.
- Human/device use requires an explicit profile, certificate/key custody model, and supported client environment.
- Display safe public fingerprints and binding status only; private keys remain outside the browser service.

## 7. Required UIX Experience

### My Authenticators overview

- Show registered methods, primary/recovery role, lifecycle state, last use, expiry, and safe properties.
- Identify gaps such as no recovery method or only one remaining usable authenticator.
- Avoid a generic “security score.”

### Add authenticator

- Present only methods enabled for the tenant/profile and compatible with the browser/device.
- Explain privacy, portability, recovery, device dependence, and assurance characteristics before enrollment.
- Use step-by-step challenge ceremonies with accessible progress, retry, cancellation, and expiry.

### Authenticator detail

- Show safe metadata, properties, provenance, recent lifecycle events, rename, verify, replace, suspend/revoke eligibility, and recovery effect.
- Never render secret or raw attestation blobs by default.

### Recovery center

- Show recovery methods, recovery-code count, last rotation/use, recovery policy, and safe alternatives.
- Require recent strong authentication for adding/removing recovery methods when possible.
- Provide an account-lockout warning before removing the final usable method.

### Tenant policy

- Configure allowed, required, prohibited, and step-up-eligible authenticator kinds/properties.
- Support enrollment grace periods, recovery controls, attestation policy, allowed algorithms, and high-risk action requirements.
- Preview affected users and lockout risk before publish.
- Version, diff, simulate, approve, activate, and roll back policy.

### Help-desk administration

- Show only safe enrollment metadata.
- Separate suspend, require re-enrollment, begin recovery, and revoke.
- Require reason, ticket/case reference where configured, approval for high-impact operations, and immutable audit.
- Never let help desk enroll an authenticator on behalf of a user without a separately designed supervised ceremony.

### Authentication context explorer

- Show required versus achieved ACR/AAL, AMR, and properties for a session/action.
- Explain which authenticators contributed and why a requirement passed or failed.
- Do not expose policy internals or sensitive device information to unauthorized users.

## 8. Security and Privacy Requirements

- Enrollment, replacement, linking, and removal require recent authentication appropriate to their risk.
- Prevent self-lockout and administrator-induced lockout unless an audited break-glass process exists.
- Bind all challenges to subject, tenant, operation, origin/RP/audience, expiry, and single-use replay state.
- Store password/OTP/recovery/passkey material through provider-owned secure storage; UIX never handles persistent secrets.
- Apply rate limits, abuse detection, retry budgets, and safe errors without identity enumeration.
- Exclude credentials, challenges, attestation objects, recovery values, device identifiers, subjects, and raw context from analytics.
- Minimize correlation: prefer pairwise identifiers, redacted device metadata, and privacy-preserving attestation.
- Require negative tests for replay, cross-account binding, cross-tenant access, origin/RP mismatch, cloned counter behavior, account-link takeover, recovery abuse, and final-factor deletion.

## 9. Team Requirements

### Technical marketing

- Provide stable screenshots for method overview, passkey enrollment, OTP verification, recovery-code rotation, tenant policy, and step-up explanation.
- Demonstrate phishing-resistant options only with the precise authenticator/property evidence.
- Distinguish supported provider primitives, repository checkpoint lifecycle, and production-ready enrollment.
- Avoid “passwordless,” “unphishable,” “device trusted,” and universal MFA claims without scoped proof.

### Developer relations

- Provide tested integration journeys for enrollment start/finish, authentication, recovery, replacement, revocation, and context evaluation.
- Explain WebAuthn RP ID/origin, OTP seed handling, recovery-code safety, federation linking, and recent-auth requirements.
- Supply deterministic virtual-authenticator fixtures and representative negative cases.
- Document how Public UIX and My Account integrate without owning lifecycle logic.

### Sales and account management

- Provide resettable scenarios: add passkey, add OTP/recovery, require step-up, suspend compromised method, recover safely.
- Include “what this proves / what it does not prove” for attestation, device binding, phishing resistance, and assurance.
- Show profile/version, policy state, fixture status, and known limitations.
- Avoid promising device management, fraud detection, or identity proofing from authenticator data alone.

### GTM strategy

- Position the pairing around governed authenticator lifecycle and explainable assurance.
- Track privacy-safe method category, ceremony stage/outcome, policy preview/publish, docs/evidence engagement, and handoff.
- Never emit user, tenant, credential, device, challenge, attestation, recovery, or context values.
- Use one taxonomy for authenticator, factor, method, credential, proof, recovery, enrollment, verification, and assurance.

### Copywriter

- Distinguish passkey, security key, OTP, recovery code, password, federated sign-in, certificate, and proof-of-possession.
- Explain “phishing resistant,” “user verified,” “device bound,” “synced,” “hardware backed,” ACR/AAL, and AMR conservatively.
- Write enrollment, expiry, retry, replacement, suspension, revocation, recovery, and lockout copy.
- Avoid blaming users for failed ceremonies or revealing whether an account exists.

## 10. Frontend Engineering Instructions

1. Implement durable authenticator, ceremony, policy, context, and audit contracts before UI activation.
2. Keep provider verification inside owning packages; the API orchestrates lifecycle and authorization.
3. Generate typed clients from the new product contract and enforce separate current-subject and tenant-admin path allowlists.
4. Build ceremonies as explicit state machines with expiry, cancellation, replay protection, and route recovery.
5. Use WebAuthn browser APIs directly only through a tested adapter; retain raw response only long enough to submit.
6. Build one-time secret components for OTP seed and recovery codes that clear on acknowledgment, timeout, navigation, and unmount.
7. Implement policy preview and lockout simulation before activation.
8. Add virtual-authenticator, negative-security, cross-tenant, privilege, accessibility, and responsive end-to-end tests.
9. Integrate Public UIX for challenge prompts and My Account for self-service links; do not duplicate provider logic.
10. Add maturity gates so absent models/context/evidence cannot render as enabled production capability.

## 11. UIX Designer Instructions

- Extend the Public/My Account visual language for self-service and the Tenant Admin console language for policy/help desk.
- Make authenticator kind, lifecycle, recovery role, properties, and last use understandable without color alone.
- Design ceremonies for browser/device interruption, timeout, retry, cancellation, and cross-device handoff.
- Present attestation and assurance through progressive disclosure with plain-language caveats.
- Design one-time secret reveal/acknowledgment and final-factor deletion safeguards.
- Provide empty/no-recovery, one-factor, many-device, unsupported browser, failed attestation, expired ceremony, lockout-risk, compromised, and recovery states.
- Validate focus, screen-reader announcements, high zoom, reduced motion, platform authenticator prompts, and WCAG 2.2 AA.

## 12. Copy Deliverables

Produce:

- authenticator catalog names/descriptions and compatibility guidance;
- enrollment, verification, replacement, suspension, revocation, and recovery flows;
- passkey/OTP/recovery/federation/mTLS/DPoP explanations;
- authentication-context and assurance glossary;
- tenant policy fields, preview, lockout warnings, approval, and rollback language;
- help-desk reason/impact, audit, unauthorized, unavailable, expiry, retry, and support copy.

## 13. Delivery Phases

### Phase 0: Canonical contracts

- Complete authenticator and passkey/WebAuthn storage models.
- Complete authentication-context vocabulary and required-versus-achieved contracts.
- Define credential-use decisions, ceremonies, lifecycle, and audit.
- Threat-model recovery, account linking, help desk, and lockout.

### Phase 1: Current-subject foundations

- Password change/recovery integration.
- OTP and recovery-code lifecycle.
- Authenticator overview/detail.
- One-time secret handling and audit.

### Phase 2: WebAuthn/passkeys

- Registration/authentication ceremonies.
- Synced/device-bound and attestation-safe metadata.
- Virtual-authenticator interoperability and negative tests.

### Phase 3: Tenant policy and support

- Policy versioning/simulation.
- Help-desk suspension/re-enrollment/recovery.
- Required/achieved context explorer and step-up integration.

### Phase 4: Advanced bindings

- Federated account binding.
- Profile-specific mTLS/DPoP human/device use.
- Attestation API integration and advanced authenticator adapters.

## 14. Acceptance Criteria

- A dedicated API owns human authenticator lifecycle without absorbing workload/client/API credentials.
- Current-subject and tenant-admin boundaries are separate, authorized, tenant-filtered, and tested.
- Provider packages remain the verification authority; the new API owns lifecycle orchestration.
- Password, OTP, recovery code, WebAuthn/passkey, and federation flows have complete lifecycle and recovery semantics before production exposure.
- ACR/AAL, AMR, and authenticator properties use canonical separate vocabularies.
- One-time values and ceremony artifacts are never persisted, logged, analyzed, or exposed after their required step.
- Lockout, replay, origin/RP mismatch, cross-account/cross-tenant binding, recovery abuse, and account-link takeover tests pass.
- Public UIX, My Account, and Tenant Admin integrate through explicit routes without duplicating lifecycle logic.
- Accessibility, responsive visual, virtual-authenticator, contract, security, and end-to-end tests pass.

## 15. Source Evidence

- `pkgs/deprecated/tba-bases-identity-authenticator/`
- `pkgs/deprecated/tigrbl-identity-credentials-concrete/`
- `pkgs/20-providers/tba-authenticator-*/`
- `pkgs/20-providers/tba-provider-authentication-context-acr-basic/`
- `pkgs/20-providers/tba-provider-authentication-context-amr-basic/`
- `pkgs/70-facade/tba-credentials/`
- `pkgs/60-runtime/tba-runtime-identity-administration/src/tba_runtime_identity_administration/_advanced_identity_plane/`
- `pkgs/02-contracts/tba-contracts-identity/src/tba_contracts_identity/authenticators.py`
- `pkgs/02-contracts/tba-contracts-identity/src/tba_contracts_identity/credentials/`
- Public UIX, My Account, Tenant Admin, provider, WebAuthn, MFA, credential, and authentication-context tests
- Authenticator/passkey/credential/context SSOT features, planned tests, claims, and evidence
