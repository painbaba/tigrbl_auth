"""Authorization table aliases and executable runtime specifications."""

from tba_storage_authorization_policy.tables import AttributePolicy, AuthorizationInvariant, DelegatedAdminScope, InvariantEvaluation, InvariantViolation, Policy, PolicyVersion, Role, TenantMembership

from tigrbl import deriveTableSpec
from tigrbl import makeOp
from tba_durability_authorization_policy.operations.authorization import (
    assign_role,
    delegated_scope_for_subject,
    grant_delegated_scope,
    grant_membership,
    list_active_attribute_policies,
    list_active_delegated_scopes,
    list_roles_for_tenant,
    revoke_delegated_scope,
    role_names_for_principal,
    upsert_role,
    upsert_attribute_policy,
)

TenantMembershipTable = TenantMembership
DelegatedAdminScopeTable = DelegatedAdminScope
RoleTable = Role
AttributePolicyTable = AttributePolicy
AuthorizationInvariantTable = AuthorizationInvariant
InvariantEvaluationTable = InvariantEvaluation
InvariantViolationTable = InvariantViolation
PolicyTable = Policy
PolicyVersionTable = PolicyVersion

AttributePolicyRuntimeSpec = deriveTableSpec(
    AttributePolicyTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="upsert_with_conditions",
            handler=upsert_attribute_policy,
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            alias="list_active_with_conditions",
            handler=list_active_attribute_policies,
            tx_scope="read_only",
            persist="skip",
        ),
    ),
)

RoleRuntimeSpec = deriveTableSpec(
    RoleTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="create_role",
            handler=upsert_role,
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            alias="list_for_tenant",
            handler=list_roles_for_tenant,
            tx_scope="read_only",
            persist="skip",
        ),
    ),
)

TenantMembershipRuntimeSpec = deriveTableSpec(
    TenantMembershipTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="grant_membership",
            handler=grant_membership,
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="assign_role",
            handler=assign_role,
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            alias="role_names_for_principal",
            handler=role_names_for_principal,
            tx_scope="read_only",
            persist="skip",
        ),
    ),
)
DelegatedAdminScopeRuntimeSpec = deriveTableSpec(
    DelegatedAdminScopeTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="grant_scope",
            handler=grant_delegated_scope,
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="revoke_scope",
            handler=revoke_delegated_scope,
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            alias="lookup",
            handler=delegated_scope_for_subject,
            tx_scope="read_only",
            persist="skip",
        ),
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            alias="list_active",
            handler=list_active_delegated_scopes,
            tx_scope="read_only",
            persist="skip",
        ),
    ),
)

__all__ = [
    "AttributePolicyRuntimeSpec",
    "AttributePolicyTable",
    "AuthorizationInvariantTable",
    "DelegatedAdminScopeRuntimeSpec",
    "DelegatedAdminScopeTable",
    "InvariantEvaluationTable",
    "InvariantViolationTable",
    "PolicyTable",
    "PolicyVersionTable",
    "TenantMembershipRuntimeSpec",
    "TenantMembershipTable",
    "RoleRuntimeSpec",
    "RoleTable",
]
