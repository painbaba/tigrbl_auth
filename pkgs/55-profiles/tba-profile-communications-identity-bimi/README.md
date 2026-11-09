# tba-profile-communications-identity-bimi

Optional BIMI Mark Certificate and DNS readiness profile.

Install from the TBA workspace with `uv sync --extra bimi`.

- `check_readiness` inspects the selected BIMI TXT record and the sender and
  organizational domains' DMARC enforcement. It returns separate DNS and DMARC
  findings, the assertion owner after any fallback, and the published asset
  URLs. `ready` describes DNS/DMARC preflight for a mark-backed deployment.
- `verify_certificate` takes a leaf-first PEM bundle and the assertion owner.
  It checks the certificate policy, classifies CMC/VMC from the signed mark
  type, matches the assertion domain or selector-qualified SAN, and checks the
  embedded compressed logotype and its digest. The injected validator checks
  the certificate path, revocation evidence, and CT evidence.

The readiness policy uses bounded RFC 9989 discovery by default and accepts a
known organizational domain for deployments that need to reproduce a specific
boundary. It checks the legacy `pct` tag and the current `t` testing tag.
The lookup is domain-level and does not process message-local selectors or
SPF/DKIM alignment. The embedded-logo check covers format markers and basic
safety checks. Full SVG schema validation, remote asset retrieval, and mailbox
display are separate checks.

## Run the example

`scripts/bimi_check.py` composes the profile with the live TXT resolver or
with TBA's existing `ProfiledTrustAnchorProvider` and the Mark Certificate
backend. Use the `assertion.name` returned by the DNS check for the certificate
check. Pass locally obtained evidence and trust material.

```console
uv run --extra bimi python scripts/bimi_check.py dns news.example.com --selector default
uv run --extra bimi python scripts/bimi_check.py verify default._bimi.example.com mark-chain.pem --root mva-root.pem --ct-log ct-log.pem --crl http://ca.example/leaf.crl=leaf.crl --crl http://ca.example/issuer.crl=issuer.crl
```

In a TBA tenant-admin application, authorize the caller for the sending domain
first. The workspace `bimi` extra includes the optional `workflow` adapter.
It composes the profile with the shared communications identity assessment
and TBA's existing durable audit writer. The evidence callback can look up a
local bundle keyed by the discovered assertion owner.

```python
from tba_capability_communications_identity import assess_domain_onboarding, recheck_domain
from tba_durability_audit.operations.audit import append_audit_event_async
from tba_profile_communications_identity_bimi import BimiProfile
from tba_profile_communications_identity_bimi.capability_adapter import BimiDomainChecker
from tba_provider_dns_txt import DnsTxtResolver

bimi = BimiProfile(dns=DnsTxtResolver(), validator=validator)
checker = BimiDomainChecker(bimi, evidence=lambda assertion: bundles.get(assertion.name))
initial = await assess_domain_onboarding(
    sending_domain, checker=checker, audit=append_audit_event_async,
    db=db, tenant_id=tenant_id,
)
latest = await recheck_domain(
    sending_domain, checker=checker, audit=append_audit_event_async,
    db=db, tenant_id=tenant_id,
)
```

References include the [BIMI draft](https://datatracker.ietf.org/doc/html/draft-brand-indicators-for-message-identification-15),
the [Mark Certificate verification draft](https://datatracker.ietf.org/doc/html/draft-fetch-validation-vmc-wchuang-12),
the [v1.8 Mark Certificate requirements](https://bimigroup.org/resources/VMC_Requirements_latest.pdf),
and [DMARC RFC 9989](https://www.rfc-editor.org/rfc/rfc9989.html).
