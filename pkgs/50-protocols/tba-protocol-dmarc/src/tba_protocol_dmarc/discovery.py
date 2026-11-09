from tba_contracts_dns import (
    TxtResolver,
    TxtStatus,
    normalize_domain,
    versioned_records,
)

from .policy import effective_policy
from .record import parse_policy_record
from .types import DmarcRecord, PolicyDiscovery, PolicyStatus


def _discover_organization(domain: str, records: dict[str, DmarcRecord]) -> str:
    organizational = domain
    for candidate, record in records.items():
        if record.public_suffix == "n":
            return candidate
        if record.public_suffix == "y" and candidate != domain:
            labels = candidate.count(".") + 2
            return ".".join(domain.split(".")[-labels:])
        organizational = candidate
    return organizational


def discover_policy(
    dns: TxtResolver,
    domain: str,
    organizational_domain: str | None = None,
    *,
    author_exists: bool = True,
) -> PolicyDiscovery:
    """Find author, organizational or public-suffix policy in a bounded DNS walk."""
    domain = normalize_domain(domain)
    labels = domain.split(".")
    if organizational_domain is not None:
        organizational_domain = normalize_domain(organizational_domain)
        if domain != organizational_domain and not domain.endswith(
            "." + organizational_domain
        ):
            raise ValueError("organizational domain must contain the sending domain")
        candidates = tuple(dict.fromkeys((domain, organizational_domain)))
    else:
        # RFC 9989 bounds a deep tree walk to the starting name and seven suffixes.
        suffixes = tuple(
            ".".join(labels[-count:]) for count in range(min(len(labels) - 1, 7), 0, -1)
        )
        candidates = (domain, *suffixes)
    records: dict[str, DmarcRecord] = {}
    for candidate in candidates:
        name = f"_dmarc.{candidate}"
        answer = dns.lookup_txt(name)
        if answer.status is TxtStatus.TEMPORARY_FAILURE:
            return PolicyDiscovery(
                PolicyStatus.TEMPORARY_FAILURE,
                organizational_domain,
                name,
                reason="DMARC DNS lookup failed",
            )
        matches = versioned_records(answer.records, b"DMARC1")
        if not matches:
            continue
        try:
            if len(matches) != 1:
                raise ValueError("multiple DMARC records")
            records[candidate] = parse_policy_record(matches[0])
        except ValueError as exc:
            return PolicyDiscovery(
                PolicyStatus.INVALID, organizational_domain, name, reason=str(exc)
            )
        if (
            records[candidate].public_suffix in {"y", "n"}
            and organizational_domain is None
        ):
            break

    if organizational_domain is None:
        organizational_domain = _discover_organization(domain, records)

    organizational = records.get(organizational_domain)
    if organizational is not None and organizational.public_suffix == "y":
        organizational = None
    if domain in records:
        source = domain
    elif organizational is not None:
        source = organizational_domain
    else:
        source = next(
            (name for name, record in records.items() if record.public_suffix == "y"),
            None,
        )
    if source is None:
        return PolicyDiscovery(PolicyStatus.MISSING, organizational_domain)

    record = records[source]
    return PolicyDiscovery(
        PolicyStatus.FOUND,
        organizational_domain,
        f"_dmarc.{source}",
        effective_policy(
            record, inherited=source != domain, author_exists=author_exists
        ),
        record,
        organizational,
    )
