from uuid import UUID

from .audit import check_and_audit
from .contracts import AuditWriter, DomainCheck, DomainChecker


async def assess_domain_onboarding(
    domain: str,
    *,
    checker: DomainChecker,
    audit: AuditWriter,
    db: object,
    tenant_id: UUID,
) -> DomainCheck:
    """Run and audit the initial domain assessment."""
    return await check_and_audit(
        domain,
        action="onboarding_assessed",
        checker=checker,
        audit=audit,
        db=db,
        tenant_id=tenant_id,
    )
