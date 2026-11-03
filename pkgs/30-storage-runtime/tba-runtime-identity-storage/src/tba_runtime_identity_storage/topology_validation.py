"""Runtime validation for identity topology scenarios."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from tba_contracts_identity.topology import (
    AxisCardinality,
    IdentityTopologyScenario,
    cardinality_for_count,
    identity_topology_scenario,
)


@dataclass(frozen=True, slots=True)
class IdentityTopologySnapshot:
    realms: tuple[Any, ...] = ()
    tenants: tuple[Any, ...] = ()
    users: tuple[Any, ...] = ()
    principals: tuple[Any, ...] = ()
    tenant_memberships: tuple[Any, ...] = ()
    subject_aliases: tuple[Any, ...] = ()


@dataclass(frozen=True, slots=True)
class ObservedIdentityTopology:
    realm_ids: tuple[str, ...]
    tenant_ids: tuple[str, ...]
    identity_ids: tuple[str, ...]
    tenant_realm_ids: tuple[str, ...]
    identity_tenant_ids: tuple[str, ...]
    identity_realm_ids: tuple[str, ...]

    @property
    def realm(self) -> AxisCardinality | None:
        return cardinality_for_count(len(self.realm_ids))

    @property
    def tenant(self) -> AxisCardinality | None:
        return cardinality_for_count(len(self.tenant_ids))

    @property
    def identities(self) -> AxisCardinality | None:
        return cardinality_for_count(len(self.identity_ids))


@dataclass(frozen=True, slots=True)
class IdentityTopologyValidationReport:
    scenario: IdentityTopologyScenario
    observed: ObservedIdentityTopology
    failures: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.failures


def _field(row: Any, name: str, default: Any = None) -> Any:
    if isinstance(row, Mapping):
        return row.get(name, default)
    return getattr(row, name, default)


def _present(value: Any) -> bool:
    return value not in {None, "", False}


def _id(value: Any) -> str | None:
    if not _present(value):
        return None
    return str(value)


def _row_id(row: Any) -> str | None:
    return _id(_field(row, "id"))


def _unique(values: Iterable[Any]) -> tuple[str, ...]:
    normalized = {_id(value) for value in values}
    return tuple(sorted(value for value in normalized if value))


def _identity_key(prefix: str, value: Any) -> str | None:
    ident = _id(value)
    if ident is None:
        return None
    return f"{prefix}:{ident}"


def observe_identity_topology(
    snapshot: IdentityTopologySnapshot,
) -> ObservedIdentityTopology:
    realm_ids = _unique(_row_id(row) for row in snapshot.realms)
    tenant_ids = _unique(_row_id(row) for row in snapshot.tenants)

    identity_ids: set[str] = set()
    identity_tenant_ids: set[str] = set()
    identity_realm_ids: set[str] = set()

    for user in snapshot.users:
        key = _identity_key("user", _row_id(user))
        if key:
            identity_ids.add(key)
        tenant_id = _id(_field(user, "tenant_id"))
        if tenant_id:
            identity_tenant_ids.add(tenant_id)

    for principal in snapshot.principals:
        key = _identity_key(
            "principal", _row_id(principal) or _field(principal, "subject")
        )
        if key:
            identity_ids.add(key)
        tenant_id = _id(_field(principal, "tenant_id"))
        realm_id = _id(_field(principal, "realm_id"))
        if tenant_id:
            identity_tenant_ids.add(tenant_id)
        if realm_id:
            identity_realm_ids.add(realm_id)

    for membership in snapshot.tenant_memberships:
        key = _identity_key("principal", _field(membership, "principal_id"))
        if key:
            identity_ids.add(key)
        tenant_id = _id(_field(membership, "tenant_id"))
        if tenant_id:
            identity_tenant_ids.add(tenant_id)

    for alias in snapshot.subject_aliases:
        key = _identity_key("principal", _field(alias, "principal_id"))
        if key is None:
            issuer = _id(_field(alias, "issuer"))
            subject = _id(_field(alias, "subject"))
            if issuer and subject:
                key = f"alias:{issuer}:{subject}"
        if key:
            identity_ids.add(key)
        tenant_id = _id(_field(alias, "tenant_id"))
        if tenant_id:
            identity_tenant_ids.add(tenant_id)

    return ObservedIdentityTopology(
        realm_ids=realm_ids,
        tenant_ids=tenant_ids,
        identity_ids=tuple(sorted(identity_ids)),
        tenant_realm_ids=_unique(
            _field(tenant, "realm_id") for tenant in snapshot.tenants
        ),
        identity_tenant_ids=tuple(sorted(identity_tenant_ids)),
        identity_realm_ids=tuple(sorted(identity_realm_ids)),
    )


def _check_axis(
    failures: list[str],
    *,
    axis: str,
    expected: AxisCardinality,
    observed: AxisCardinality | None,
    count: int,
) -> None:
    if observed != expected:
        failures.append(
            f"{axis} cardinality expected {expected}, observed {observed or 'none'} ({count})"
        )


def validate_identity_topology_snapshot(
    snapshot: IdentityTopologySnapshot,
    scenario_id: int,
) -> IdentityTopologyValidationReport:
    scenario = identity_topology_scenario(scenario_id)
    observed = observe_identity_topology(snapshot)
    failures: list[str] = []

    _check_axis(
        failures,
        axis="realm",
        expected=scenario.realm,
        observed=observed.realm,
        count=len(observed.realm_ids),
    )
    _check_axis(
        failures,
        axis="tenant",
        expected=scenario.tenant,
        observed=observed.tenant,
        count=len(observed.tenant_ids),
    )
    _check_axis(
        failures,
        axis="identities",
        expected=scenario.identities,
        observed=observed.identities,
        count=len(observed.identity_ids),
    )

    realm_set = set(observed.realm_ids)
    tenant_set = set(observed.tenant_ids)
    tenant_realm_set = set(observed.tenant_realm_ids)
    identity_tenant_set = set(observed.identity_tenant_ids)
    identity_realm_set = set(observed.identity_realm_ids)

    unknown_tenant_realms = sorted(tenant_realm_set - realm_set)
    if unknown_tenant_realms:
        failures.append(f"tenants reference unknown realms: {unknown_tenant_realms}")

    unknown_identity_tenants = sorted(identity_tenant_set - tenant_set)
    if unknown_identity_tenants:
        failures.append(
            f"identities reference unknown tenants: {unknown_identity_tenants}"
        )

    unknown_identity_realms = sorted(identity_realm_set - realm_set)
    if unknown_identity_realms:
        failures.append(
            f"identities reference unknown realms: {unknown_identity_realms}"
        )

    if scenario.realm == "multi" and len(observed.realm_ids) > 1:
        tenants_without_realm = [
            _row_id(tenant) or "<unknown>"
            for tenant in snapshot.tenants
            if not _present(_field(tenant, "realm_id"))
        ]
        if tenants_without_realm:
            failures.append(
                f"multi-realm topology has tenants without realm_id: {tenants_without_realm}"
            )

    if scenario.realm == "single" and len(tenant_realm_set) > 1:
        failures.append(
            f"single-realm topology has tenants in multiple realms: {sorted(tenant_realm_set)}"
        )

    if scenario.tenant == "single" and len(identity_tenant_set) > 1:
        failures.append(
            f"single-tenant topology has identities in multiple tenants: {sorted(identity_tenant_set)}"
        )

    if observed.identity_ids and observed.tenant_ids and not identity_tenant_set:
        failures.append("identity topology has identities without tenant bindings")

    if scenario.tenant == "multi" and len(identity_tenant_set) < 2:
        failures.append(
            "multi-tenant topology must bind identities to at least two tenants"
        )

    if (
        scenario.realm == "multi"
        and scenario.tenant == "multi"
        and len(tenant_realm_set) < 2
    ):
        failures.append(
            "multi-realm multi-tenant topology must place tenants in at least two realms"
        )

    return IdentityTopologyValidationReport(
        scenario=scenario,
        observed=observed,
        failures=tuple(failures),
    )


async def collect_identity_topology_snapshot(db: Any) -> IdentityTopologySnapshot:
    from tba_storage_principals.tables import Principal, SubjectAlias, User
    from tba_storage_tenancy.tables import Realm, Tenant
    from tba_storage_authorization_policy.tables import TenantMembership
    from tigrbl_concrete.records import list_records

    return IdentityTopologySnapshot(
        realms=tuple(await list_records(Realm, db)),
        tenants=tuple(await list_records(Tenant, db)),
        users=tuple(await list_records(User, db)),
        principals=tuple(await list_records(Principal, db)),
        tenant_memberships=tuple(await list_records(TenantMembership, db)),
        subject_aliases=tuple(await list_records(SubjectAlias, db)),
    )


async def validate_identity_topology_db(
    db: Any,
    scenario_id: int,
) -> IdentityTopologyValidationReport:
    snapshot = await collect_identity_topology_snapshot(db)
    return validate_identity_topology_snapshot(snapshot, scenario_id)


__all__ = [
    "IdentityTopologySnapshot",
    "IdentityTopologyValidationReport",
    "ObservedIdentityTopology",
    "collect_identity_topology_snapshot",
    "observe_identity_topology",
    "validate_identity_topology_db",
    "validate_identity_topology_snapshot",
]
