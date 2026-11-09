# Communications Identity API + Certificate/Attestation UIX Requirements Brief

**Pairing:** `tba-router-communications-identity` + `@tba/communications-identity-uix`<br>
**Opportunity-map item:** 18<br>
**Primary buyers:** telecom operators, regulated communications teams, customer-support platforms, brand/email security teams, legal operations, and API platform teams<br>
**Status:** proposed profile/orchestration surface; certificate, JOSE, trust, attestation, policy, and audit foundations exist

## 1. Product Decision

Build a profile-driven communications identity control plane for proving who or what signed a communication, which identity or authority was asserted, what content/context was covered, and whether that proof remained valid under a named channel profile.

Initial profile families:

- STIR/SHAKEN caller identity for SIP voice;
- BIMI with VMC/CMC evidence for brand indicators in supported email ecosystems;
- S/MIME signing and encryption identities;
- document-signing identities and evidence;
- webhook and API message-signing identities.

These profiles share lifecycle, custody, authorization, evidence, and UI components, but they do not share identical trust semantics. The product must preserve the native rules of each channel rather than inventing one generic “verified communication” badge.

## 2. Product Promise

For each supported communication, the product should answer:

1. Who or what requested the signature or assertion?
2. Which organization, domain, telephone number, mailbox, document signer, service, or endpoint was represented?
3. What authority allowed that representation?
4. Which fields/content were cryptographically covered?
5. Which certificate, key, trust framework, and profile were used?
6. Was the proof valid, fresh, authorized, and non-replayed at verification time?
7. What does the proof establish—and what does it not establish?

## 3. Current Repository Reality

Reusable foundations include:

- Certificate Lifecycle API direction for roots/intermediates, profiles, issuance, custody, validation, revocation, renewal, and evidence;
- JOSE signing/verification, algorithm policy, JWKS, key rotation, and JWT claims;
- Trust Registry direction for scoped authorities, issuers, certificate roots, profiles, algorithms, and point-in-time resolution;
- federation and attestation chains;
- principal, tenant, service, workload, client, domain, policy, delegation, and audit concepts;
- token, proof-of-possession, nonce, replay, and transaction-context capabilities.

The optional BIMI library covers sender DNS/DMARC readiness and verification of supplied VMC/CMC evidence. The Communications Identity API and UIX, certificate enrollment and renewal, and the other channel profiles in this brief remain proposed.

## 4. Users and Jobs

### Communications security administrator

- Register identities, channels, authorities, profiles, and signing policies.
- Bind people/services to approved telephone numbers, domains, mailboxes, templates, or endpoints.
- control key custody and signing authorization.
- monitor expiry, failure, misuse, and incident response.

### Telecom or email operator

- operate high-volume signing/verification with strict latency and availability.
- trace trust and policy failures without exposing private keys or message content.
- coordinate certificate and authority changes.

### Brand and domain owner

- prove domain/control and mark evidence through the applicable program.
- publish required DNS and certificate references safely.
- monitor readiness without assuming mailbox-provider display.

### Document signer or legal operations user

- review the exact document and signing intent.
- authenticate and sign with the correct organizational/personal authority.
- receive a durable evidence package and validation result.

### API/webhook developer

- create a signing profile covering the correct HTTP components.
- rotate keys and publish verification metadata.
- test canonicalization, freshness, replay, and intermediary behavior.

### Auditor, support engineer, or incident responder

- reconstruct an assertion without broad access to message/document content.
- identify affected identities, keys, channels, and recipients.
- suspend signing, publish status, and verify recovery.

## 5. Architectural Ownership

### Communications Identity API owns

- channel profiles and profile versions;
- communication identities and verified bindings;
- signer/asserter authorization and delegation;
- signing/attestation requests and policy orchestration;
- profile-native payload construction and verification adapters;
- assertion metadata, evidence, validation receipts, and channel incidents;
- DNS/publication readiness and external-consumer observations where applicable.

### Existing products retain ownership

- Certificate Center: CA integration, certificate issuance, custody references, renewal, revocation, path validation, OCSP/CRL.
- Trust Registry: recognized authorities, roots, roles, profile acceptance, algorithms, jurisdictions, and point-in-time trust.
- JOSE/crypto: signing and verification primitives.
- Attestation Center: evidence verification/appraisal.
- Security Signals: compromise and status-change distribution.
- Principals/policy/delegation: actor authority and transaction authorization.
- Audit: durable operator/security events.

### External ecosystem responsibility

Telephone authorities, STI governance, certificate authorities, mailbox providers, trademark offices, trust-service providers, document ecosystems, DNS operators, and receiving API systems remain authoritative for their respective policies and outcomes.

## 6. Shared Communication Identity Model

A communication identity records:

- tenant, organization, owner, and environment;
- channel and profile version;
- represented identifier: telephone number/range, domain, mailbox, legal/person identity, document role, service, endpoint, or key ID;
- authority/binding evidence and verification method;
- allowed actors, workloads, clients, and delegated signers;
- signing key/certificate reference and custody class;
- permitted purposes, templates, destinations, origination systems, and risk tier;
- assurance/authentication requirements;
- effective, renewal, suspension, and expiry times;
- publication/discovery metadata;
- status, incident, and audit references.

Bindings must be versioned and point-in-time resolvable. Reassigning a telephone number, domain, mailbox, role, or service cannot rewrite prior evidence.

## 7. Shared Signing and Verification Pipeline

### Signing

1. Authenticate actor/workload and validate tenant.
2. Resolve communication identity and active authority binding.
3. Validate purpose, target, content/template, assurance, risk, and delegation.
4. Build the profile-native canonical signing input.
5. Sign through HSM/KMS/external signer without exporting the private key.
6. Attach native headers, tokens, certificates, timestamps, or evidence.
7. Record a secret-safe, content-minimized evidence receipt.

### Verification

1. Parse with strict size/profile bounds.
2. reconstruct the profile-native canonical input.
3. resolve key/certificate and chain under a named trust policy.
4. validate signature, algorithm, identity binding, time, status, authority, and required fields.
5. enforce freshness, nonce, sequence, and replay policy where the profile supports it.
6. return `valid`, `invalid`, `indeterminate`, `stale`, or `unsupported` with reasons.
7. state the exact components and identity that were proven.

Cryptographic validity and authorization are separate results.

## 8. STIR/SHAKEN Profile

The profile must integrate the IETF STIR architecture and the applicable SHAKEN governance profile rather than minting a proprietary caller badge.

Required capabilities:

- telephone number/range inventory and authority evidence;
- STI certificate profile, chain, TN authorization list or ecosystem-native equivalent;
- originating-service authorization and attestation-level policy;
- PASSporT construction and signing;
- SIP Identity header integration through a telecom adapter;
- verification, certificate/status retrieval, and reason mapping;
- origination identifier and call correlation;
- key/certificate rollover without dropped traffic;
- high-throughput, low-latency operation with safe degradation;
- robocall/abuse analytics integration as a separate signal.

Attestation level describes the signer’s asserted relationship to the calling party/number under the profile. It does not prove call content is truthful, the call is wanted, or the caller is harmless.

Profile support must identify deployment jurisdiction and governance authority. SHAKEN program roles and certificate eligibility are not universally portable.

## 9. BIMI and Mark Certificate Profile

The first library slice is available through the [BIMI profile](../../../pkgs/55-profiles/tba-profile-communications-identity-bimi/README.md) and the optional `bimi` workspace extra. It checks BIMI TXT and DMARC enforcement, verifies the Mark Certificate against configured roots, CRLs and CT keys, and binds the leaf to the assertion owner and its embedded logo. The requirements below cover the wider product surface.

The profile composes standalone BIMI and DMARC protocol packages, shared DNS contracts, an X.509 subject logotype decoder, and a certificate evidence provider. Its optional workflow adapter uses the shared Communications Identity capability to run and audit an initial domain assessment or a follow-up check.

Required capabilities:

- organizational domain and DNS-control verification;
- DMARC-readiness inputs and enforcement checks;
- BIMI DNS record construction, linting, lookup, and propagation observation;
- SVG Tiny P/S validation and safe rendering;
- VMC/CMC request metadata, CA integration, certificate lifecycle, and evidence references;
- domain/mark/certificate binding checks;
- public asset hosting health and content-integrity monitoring;
- mailbox-provider observation separated from protocol readiness;
- renewal, replacement, incident, and rollback workflows.

The product must distinguish:

- DNS record valid;
- DMARC posture satisfies the selected profile;
- SVG valid;
- mark certificate valid and domain-bound;
- mailbox provider eligible;
- logo actually displayed.

BIMI/VMC/CMC does not guarantee delivery, inbox placement, display by every provider, sender honesty, or absence of phishing.

Uploaded SVGs are untrusted active content. Validate against the selected profile, strip/reject external references and scripting, render in isolation, and preserve a reviewed digest.

## 10. S/MIME Profile

Required capabilities:

- mailbox/person/organization identity proof and certificate enrollment;
- separate signing and encryption key/profile policy;
- certificate discovery/distribution and recipient-certificate validation;
- S/MIME 4.0 MIME/CMS construction and verification;
- canonicalization and client interoperability tests;
- signed-only, enveloped-only, and signed-and-enveloped modes as explicitly supported;
- certificate renewal, revocation, key rollover, and historical signature validation;
- encryption-key recovery/escrow only under a separately approved policy;
- organizational versus personal signer identity clarity;
- gateway signing clearly identified as gateway behavior.

A valid S/MIME signature establishes integrity over covered MIME content and association with the signing certificate. It does not establish that every visible mail-client field was covered, the sender’s statement was true, or the recipient should trust attachments.

The UI must show covered content/header limitations and distinguish signature validation from sender policy.

## 11. Document-Signing Profile

Document signing must be adapter/profile based: PDF signatures, CMS/XML signing, remote-signing services, or jurisdictional qualified-signature profiles have different requirements.

Shared requirements:

- immutable document bytes and digest before authorization;
- signer identity, organizational role, authority, and intent;
- human-readable document preview tied to the signed digest;
- strong authentication and explicit consent at signing time;
- signature format/profile, certificate chain, timestamp, revocation, and validation data;
- multi-signer order, countersignature, witnessing, seal, and approval semantics where profiled;
- long-term validation/archive evidence where required;
- tamper-evident audit and downloadable validation report;
- correction only through new document/version/signature, never mutation.

Legal effect depends on jurisdiction, signature type, identity proofing, intent, document/process, trust-service status, and evidence. The UI and copy must not label every cryptographic signature “legally binding,” “qualified,” or “notarized.”

## 12. Webhook and HTTP Message Signature Profile

Use RFC 9421 for standards-based HTTP Message Signatures where interoperability permits. Maintain explicit legacy adapters only for named vendor schemes.

A signing profile defines:

- signer identity and key discovery method;
- algorithm and key ID;
- covered components, including method, target, authority, content digest, and selected headers;
- signature creation/expiry window;
- nonce, request ID, sequence, or event ID replay policy;
- canonicalization and proxy/transformation assumptions;
- body/content encoding and digest rules;
- retry behavior and idempotency relationship;
- key rotation overlap and verifier cache policy;
- error/response-signature requirements.

Verification must report which components were covered. A valid signature over too few components may be cryptographically valid but policy-invalid.

HTTP signatures do not encrypt the message, stop replay without application policy/state, or prove that an upstream business event is true.

## 13. Key Custody and Signing Authority

- Private signing keys default to HSM/KMS/external-signer custody and are non-exportable where supported.
- Separate keys by tenant, environment, channel, identity, profile, and purpose according to risk.
- Enforce algorithm/profile policy at the signing boundary.
- Bind signing authorization to content/request digest and communication identity.
- Record actor and subject separately for delegated/gateway signing.
- Require quorum or stronger controls for CA/authority and high-impact organizational signing keys.
- Support staged rotation with verifier/publication propagation checks.
- Suspend signing immediately on compromise while preserving verification of historical artifacts under point-in-time policy.
- Do not use general OAuth/JWT signing keys for telephone, email, document, or webhook signatures merely for convenience.

## 14. Evidence, Privacy, and Data Minimization

Evidence records should contain:

- transaction/assertion ID and channel profile;
- actor, represented identity, authority, and policy-decision references;
- input/output digest, not raw message/document by default;
- signing key/certificate fingerprint and chain reference;
- profile version, algorithm, timestamps, and status checks;
- covered components/claims;
- external transport/provider correlation when safe;
- outcome and reason codes.

Raw call metadata, message bodies, recipients, telephone numbers, email addresses, documents, and webhook payloads can be highly sensitive. Store them only under an explicit product requirement, purpose, retention policy, access model, and regional/privacy review. Use keyed/pseudonymous identifiers for operational aggregation where feasible.

## 15. API Requirements

Provide versioned endpoints for:

- `/profiles` and profile versions/conformance status;
- `/communication-identities`, bindings, authority, lifecycle, and incidents;
- `/signers`, authorization, delegation, custody, and key/certificate references;
- `/sign` and `/verify` through profile-specific typed requests;
- `/telephone-identities`, ranges, certificates, signing/verification policy;
- `/email-identities`, S/MIME enrollment, BIMI assets/DNS/readiness;
- `/document-signing`, templates, ceremonies, signatures, and validation;
- `/webhook-signing`, profiles, keys, test events, and verification;
- `/publications`, DNS/metadata/key propagation and observations;
- `/evidence`, receipts, validation reports, and exports;
- `/incidents`, suspension, impact, notifications, and recovery.

API rules:

- use distinct media types/schemas per profile;
- require content digests and idempotency for signing operations;
- enforce payload size and type bounds;
- never accept arbitrary signer/key identifiers without server-side authorization resolution;
- return machine-readable verification sub-results;
- provide asynchronous jobs for document ceremonies, issuance, DNS propagation, and bulk operations;
- support safe detached-signing patterns so sensitive content need not be uploaded when the profile permits;
- keep private keys and root connector credentials out of all responses.

## 16. Certificate/Attestation UIX

### Communications identity overview

Show channel inventory, active identities, certificate/key expiry, publication health, signing/verification failures, unauthorized attempts, incident state, profile conformance, and volume/latency without exposing message contents.

### Identity onboarding

Use channel-specific wizards. Shared steps are owner, represented identifier, authority proof, signer authorization, custody, profile, publication, test, approval, and activation. Never imply that technical validation completes external governance approval.

### Voice identity center

Provide number/range ownership, certificate, attestation policy, originating systems, test call assertion, verification diagnostics, throughput, expiry, and incident views. Show attestation meaning and limitations in-context.

### Brand/email identity center

Separate BIMI readiness from S/MIME lifecycle. BIMI view shows DMARC input, DNS, SVG, certificate, hosting, provider observations, and exact blockers. S/MIME view shows mailbox identities, signing/encryption certificates, client compatibility, expiry, and validation.

### Document signing studio

Show templates/profiles, signer/role requirements, custody, ceremony, document digest/preview, multi-signer state, timestamps, validation, and evidence. Signing confirmation must name the signer identity, role, document, and legal/profile caveat.

### Webhook signing studio

Provide endpoint/profile setup, covered-component builder, sample request, canonical base, signature headers, verification code, replay store configuration, key rotation test, and intermediary simulation.

### Verification workbench

Allow safe test artifacts and return layered results: parse, canonicalization, signature, certificate/key, identity binding, authority, time/status, replay, and policy. Redact content by default and never retain uploaded samples without explicit consent.

### Incident and evidence center

Support scoped suspension, key compromise, certificate revoke/replace, publication updates, verifier notifications, impact analysis, and recovery. Evidence views separate cryptographic proof from business/legal conclusions.

## 17. Security, Privacy, and Reliability

- Enforce tenant, environment, channel, identity, and purpose separation.
- Separate identity proofing, signer authorization, profile administration, key custody, signing, audit, and incident roles.
- Require step-up or workload attestation for high-impact signing.
- Protect private keys using non-exportable custody and tightly scoped signer APIs.
- Prevent signing-oracle abuse with exact profile schemas, authorization, rate limits, payload bounds, and anomaly detection.
- Prevent cross-protocol/key confusion with key purposes, certificate profiles, media types, and domain-separated inputs.
- Verify canonical bytes/digests shown to humans match bytes signed.
- Enforce replay state for webhook/document/transaction profiles where applicable.
- Defend parsers/renderers against malformed SIP, MIME/CMS, ASN.1, PDF/XML, SVG, HTTP fields, archives, and decompression bombs.
- Apply SSRF controls to certificate, DNS, logo, status, and metadata retrieval.
- Preserve signing availability without failing open on identity/authority checks.
- Make verification degradation explicit when trust/status/time sources are unavailable.
- Use immutable audit/evidence with retention and legal hold where authorized.
- Meet WCAG 2.2 AA, including document/signature and dense diagnostic workflows.

## 18. Stakeholder Requirements

### Technical marketing

Build separate, accurate demos for caller attestation, BIMI readiness, S/MIME signing, document ceremony, and webhook verification. Show failure cases and “what this proves.” Never combine channel outcomes into one universal verified badge.

### Developer relations

Deliver profile SDKs, SIP/webhook adapters, certificate enrollment examples, MIME/CMS and RFC 9421 test vectors, DNS/BIMI lint tools, document-validation fixtures, safe key-custody integration, rotation guides, and negative/replay/canonicalization examples.

### Sales and account management

Use channel-specific discovery: jurisdiction, governance authority, carriers/mail providers/document ecosystems, domains/numbers/mailboxes, signing volume/latency, key custody, CAs/trust services, client interoperability, legal requirements, data retention, and incident SLAs. Map external approvals and dependencies explicitly.

### GTM strategist

Treat each channel as its own offer and partner motion. Start with webhook signing and organizational certificates where dependencies are controllable; pursue telecom, mark certificates, and regulated document signing through qualified ecosystem partners and jurisdiction profiles.

### Copywriter

Create profile-specific vocabularies and qualification rules. Prefer `signature valid`, `identity binding valid`, `authorized for`, `attestation level`, `BIMI ready`, `provider observed`, and `validation indeterminate`. Avoid `verified caller`, `fraud-free`, `guaranteed display`, `secure email`, and `legally binding` without exact scope.

## 19. Delivery Instructions

### Frontend engineer

- Generate profile-specific typed clients; do not use a generic untyped sign form.
- Keep sensitive content out of URLs, logs, analytics, session replay, and browser persistence.
- Use Web Workers/sandboxed renderers where safe local parsing/preview is needed.
- Implement server-side paging and aggregated telemetry for high-volume assertions.
- Render layered verification results and external dependency freshness.
- Require diff/preview/approval for identity binding, signer authority, key, profile, and publication changes.
- Provide accessible non-visual equivalents for certificate chains, signature coverage, and timelines.

### UIX designer

- Use a shared shell but distinct channel workspaces and terminology.
- Visually separate identity, authority, cryptographic validity, delivery/display, and business/legal meaning.
- Design unknown, unsupported, stale, partial, externally pending, degraded, and compromised states.
- Make signed content/components clear before human approval.
- Keep evidence concise by default with expert drill-down.
- Test with telecom, email, legal, and API users rather than assuming one operator persona.

### Copywriter

- Write “what it proves / does not prove” for every profile and result.
- Explain external provider/authority dependencies without blaming users.
- Use neutral language for fraud/spam risk and failed verification.
- Write irreversible/incident warnings and recovery guidance.

## 20. Delivery Phases

### Phase 1: Shared platform and webhook profile

- communication identity/binding, signer authorization, evidence, incident, and profile contracts;
- HSM/KMS signer integration;
- RFC 9421 webhook signing/verification, replay controls, SDK, and UIX;
- Trust Registry and Certificate Center integration.

### Phase 2: Organizational email profiles

- S/MIME enrollment/sign/verify and interoperability matrix;
- BIMI DNS/SVG/readiness and certificate lifecycle integrations;
- email identity workspace and provider-observation separation.

### Phase 3: Document signing

- one selected PDF/CMS or remote-signing profile;
- signer ceremony, timestamp/status, multi-signer workflow, and long-term evidence;
- jurisdictional/legal review and qualified partner integrations where targeted.

### Phase 4: Telecom

- selected jurisdiction’s STIR/SHAKEN governance and certificate integrations;
- carrier/SIP adapters, performance, high availability, and conformance;
- incident coordination and scale certification before production claims.

## 21. Acceptance Criteria

### Shared API/runtime

- Every signature resolves an active communication identity, authority, signer, purpose, key, and profile.
- Actor and represented identity are distinct and auditable.
- Signing requests bind authorization to the exact digest/canonical input.
- Verification reports covered content/components and separate cryptographic, identity, authority, time/status, replay, and policy results.
- Private keys never leave approved custody.
- Rotation supports propagation overlap and historical verification.
- Suspended/expired/compromised identities cannot create new signatures.
- Evidence contains no raw communication content by default.
- Cross-tenant/profile/key-purpose misuse is denied and tested.

### Profile evidence

- RFC 9421 tests cover canonicalization, component selection, transformations, expiry, nonce/replay, rotation, and invalid signatures.
- S/MIME tests cover supported MIME/CMS modes, canonicalization, chain/status, expiry, multiple clients, and covered-header limitations.
- BIMI tests separately prove DNS, DMARC input, SVG, certificate, hosting, propagation, and provider observation states.
- Document tests bind displayed bytes/digest, signer intent, certificate/timestamp/status, modification detection, and historical validation.
- STIR/SHAKEN tests cover PASSporT/SIP integration, telephone authority, attestation policy, certificate/status, rollover, latency, and governance profile.

### UIX/business

- No channel uses a universal “verified” success label.
- Users can see what was proven and what remains external/unknown.
- High-impact changes include affected identities/channels and rollback implications.
- Core UIX meets WCAG 2.2 AA.
- Sales/marketing claims map to named profiles, external programs, and conformance evidence.

## 22. Success Measures

- signing/verification success and p95 latency by profile;
- unauthorized signing attempts denied;
- certificate/key/binding expirations prevented;
- key rotation completed without verification gaps;
- webhook replay attempts detected and rejected;
- time from compromise to signing suspension and verifier propagation;
- percentage of assertions with complete authority/evidence chain;
- BIMI readiness versus provider-observed display, reported separately;
- S/MIME client interoperability pass rate;
- document validation and evidence-reconstruction success;
- STIR/SHAKEN verification/attestation distribution without equating it to call quality;
- support incidents caused by misleading result language.

## 23. Source Evidence

### Repository

- `docs/strategy/uix-pairing-briefs/10-additional-api-uix-opportunity-map.md`
- `docs/strategy/uix-pairing-briefs/17-certificate-lifecycle-api-certificate-center-uix.md`
- `docs/strategy/uix-pairing-briefs/18-attestation-api-attestation-center-uix.md`
- `docs/strategy/uix-pairing-briefs/27-trust-registry-api-trust-registry-uix.md`
- certificate, JOSE, policy, delegation, principal, audit, token, and security-signal packages/tests.

### Standards and primary sources

- [RFC 8224](https://www.rfc-editor.org/rfc/rfc8224), [RFC 8225](https://www.rfc-editor.org/rfc/rfc8225), [RFC 8226](https://www.rfc-editor.org/rfc/rfc8226), and [RFC 8588](https://www.rfc-editor.org/rfc/rfc8588): SIP authenticated identity, PASSporT, STIR certificates, and SHAKEN PASSporT extension.
- [BIMI Group Implementation Guide](https://bimigroup.org/implementation-guide/) and [VMC/CMC resources](https://bimigroup.org/verified-mark-certificates-vmc-and-bimi/): DNS, SVG, mark-certificate, DMARC, and provider-dependency guidance.
- [RFC 8551, S/MIME 4.0](https://www.rfc-editor.org/rfc/rfc8551): MIME/CMS signing and encryption profile.
- [RFC 9421, HTTP Message Signatures](https://www.rfc-editor.org/rfc/rfc9421): signing/verifying selected HTTP message components and signature metadata.
- [RFC 9530, Digest Fields](https://www.rfc-editor.org/rfc/rfc9530): HTTP content/representation digest fields.
- [ETSI EN 319 102-1](https://www.etsi.org/deliver/etsi_en/319100_319199/31910201/) and selected PAdES/XAdES/CAdES profiles: signature creation/validation inputs for targeted European deployments; select exact current versions during implementation.

## 24. Explicit Non-Claims

- STIR/SHAKEN attestation does not prove a call is wanted, truthful, or non-malicious.
- BIMI or a mark certificate does not guarantee message delivery, inbox placement, or logo display.
- S/MIME validity does not prove every visible header was signed or that content is safe/true.
- A document’s cryptographic signature is not automatically a qualified, notarized, witnessed, or legally binding signature.
- HTTP Message Signatures do not encrypt payloads or prevent replay without freshness and application state.
- Certificate validity alone does not prove current authority to represent a telephone number, domain, mailbox, role, or service.
- Existing repository certificate/JOSE capabilities are foundations, not evidence of implemented channel-profile conformance.
- This pairing does not replace carriers, mailbox providers, DNS, CAs, trademark authorities, trust-service providers, document-management systems, or receiving API policy.
