"""Durable WebAuthn relying-party configuration operations."""

from collections.abc import Mapping
from typing import Any

from tba_storage_webauthn.tables import WebAuthnRelyingParty

from tigrbl import (
    database_from_context,
    first_table_record,
    payload_from_context,
)


async def resolve_relying_party_configuration(ctx: Mapping[str, Any]) -> object | None:
    payload = payload_from_context(ctx)
    return await first_table_record(
        WebAuthnRelyingParty,
        database_from_context(ctx),
        {
            "tenant_id": payload.get("tenant_id"),
            "rp_id": payload.get("rp_id"),
            "enabled": True,
        },
    )


resolve_allowed_origins = resolve_relying_party_configuration
resolve_registration_policy = resolve_relying_party_configuration
resolve_authentication_policy = resolve_relying_party_configuration

__all__ = [
    "resolve_allowed_origins",
    "resolve_authentication_policy",
    "resolve_registration_policy",
    "resolve_relying_party_configuration",
]
