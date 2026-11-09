from .types import DmarcRecord


def effective_policy(
    record: DmarcRecord, *, inherited: bool, author_exists: bool = True
) -> str:
    if not inherited:
        return record.policy
    if not author_exists and record.nonexistent_policy is not None:
        return record.nonexistent_policy
    return record.subdomain_policy or record.policy
