from asyncio import to_thread
from uuid import UUID

from .contracts import AuditWriter, DomainCheck, DomainChecker


async def check_and_audit(
    domain: str,
    *,
    action: str,
    checker: DomainChecker,
    audit: AuditWriter,
    db: object,
    tenant_id: UUID,
) -> DomainCheck:
    if not isinstance(tenant_id, UUID):
        raise ValueError(
            "communications identity checks require an explicit tenant UUID"
        )

    result = await to_thread(checker.check, domain)
    await audit(
        db=db,
        tenant_id=tenant_id,
        event_type=f"communications_identity.domain.{action}",
        target_type="sending_domain",
        target_id=result.domain,
        outcome=result.outcome.value,
        details={**result.details, "profile": checker.profile},
    )
    return result
