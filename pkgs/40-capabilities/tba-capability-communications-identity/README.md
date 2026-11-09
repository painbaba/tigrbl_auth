# tba-capability-communications-identity

Shared domain onboarding and recheck workflows.

Implement `DomainChecker` to supply a channel-specific assessment, and pass
an async audit writer such as `tba_durability_audit.operations.audit.append_audit_event_async`.
`assess_domain_onboarding` records an initial assessment, and
`recheck_domain` records a follow-up. Both require an explicit tenant UUID.
The calling application authorizes the domain operation and owns persistence
and scheduling.

```python
from tba_capability_communications_identity import recheck_domain
from tba_durability_audit.operations.audit import append_audit_event_async

result = await recheck_domain(
    domain,
    checker=channel_checker,
    audit=append_audit_event_async,
    db=db,
    tenant_id=tenant_id,
)
```
