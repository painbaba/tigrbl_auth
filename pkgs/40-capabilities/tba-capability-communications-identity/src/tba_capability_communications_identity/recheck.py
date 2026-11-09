from uuid import UUID

from .audit import check_and_audit
from .contracts import AuditWriter, DomainCheck, DomainChecker


async def recheck_domain(
    domain: str,
    *,
    checker: DomainChecker,
    audit: AuditWriter,
    db: object,
    tenant_id: UUID,
) -> DomainCheck:
    """Run and audit a follow-up assessment for a domain."""
    return await check_and_audit(
        domain,
        action="rechecked",
        checker=checker,
        audit=audit,
        db=db,
        tenant_id=tenant_id,
    )
