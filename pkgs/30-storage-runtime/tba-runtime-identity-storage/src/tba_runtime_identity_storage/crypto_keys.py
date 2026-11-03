"""Storage-backed crypto key execution wiring."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tba_storage_key_material.tables import CryptoKey
from tigrbl_concrete.records import create_record, first_record, update_record
from tba_contracts_security_trust import (
    AttestKeyRequest,
    DecapsulateRequest,
    DecryptRequest,
    EncapsulateRequest,
    EncryptRequest,
    ExportPublicKeyRequest,
    SignRequest,
    UnwrapKeyRequest,
    VerifyAttestationRequest,
    VerifySignatureRequest,
    WrapKeyRequest,
)

from ._crypto_keys import (
    CryptoProviderRegistry,
    ensure_allowed_op,
    jwks_from_crypto_keys,
    provider_key_ref_from_row,
    public_material_from_row,
    resolve_provider,
)


async def _key_for_operation(
    db: Any, *, kid: str, operation: str, tenant_id: Any = None
) -> Any:
    filters = {"kid": kid}
    if tenant_id is not None:
        filters["tenant_id"] = tenant_id
    row = await first_record(CryptoKey, db, filters)
    if row is None:
        raise LookupError("crypto key not found")
    ensure_allowed_op(row, operation)
    return row


def _provider(
    row: Any,
    *,
    registry: CryptoProviderRegistry | Mapping[str, Any] | None = None,
    ctx: Mapping[str, Any] | None = None,
) -> Any:
    return resolve_provider(getattr(row, "provider", None), registry=registry, ctx=ctx)


async def create_key(
    db: Any,
    *,
    provider: Any,
    kid: str,
    algorithm: str,
    spec: Any,
    storage: Mapping[str, Any] | None = None,
) -> Any:
    handle = await provider.create_key(spec)
    data = dict(storage or {})
    return await create_record(
        CryptoKey,
        db,
        {
            "kid": kid,
            "algorithm": algorithm,
            "provider": data.pop("provider", getattr(handle, "provider", None)),
            "provider_key_ref": data.pop(
                "provider_key_ref", getattr(handle, "ref", None)
            ),
            "public_material": data.pop(
                "public_material", getattr(handle, "public_material", None)
            ),
            "public_material_format": data.pop(
                "public_material_format",
                getattr(handle, "public_material_format", None),
            ),
            "fingerprint": data.pop(
                "fingerprint", getattr(handle, "fingerprint", None)
            ),
            **data,
        },
    )


async def rotate_key(
    db: Any,
    *,
    kid: str,
    registry: CryptoProviderRegistry | Mapping[str, Any] | None = None,
    ctx: Mapping[str, Any] | None = None,
    spec_overrides: Mapping[str, Any] | None = None,
) -> Any:
    row = await _key_for_operation(db, kid=kid, operation="rotate")
    provider = _provider(row, registry=registry, ctx=ctx)
    handle = await provider.rotate_key(kid, spec_overrides=spec_overrides)
    return await update_record(
        CryptoKey,
        db,
        getattr(row, "id"),
        {
            "provider": getattr(handle, "provider", getattr(row, "provider", None)),
            "provider_key_ref": getattr(handle, "ref", None),
            "public_material": getattr(handle, "public_material", None),
            "public_material_format": getattr(handle, "public_material_format", None),
        },
    )


async def sign(
    db: Any,
    *,
    kid: str,
    payload: bytes | str,
    registry: CryptoProviderRegistry | Mapping[str, Any] | None = None,
    ctx: Mapping[str, Any] | None = None,
    alg: str | None = None,
    tenant_id: Any = None,
) -> Any:
    row = await _key_for_operation(db, kid=kid, operation="sign", tenant_id=tenant_id)
    provider = _provider(row, registry=registry, ctx=ctx)
    return await provider.sign(
        SignRequest(payload=payload, key=provider_key_ref_from_row(row), alg=alg)
    )


async def verify(
    db: Any,
    *,
    kid: str,
    payload: bytes | str,
    signature: bytes | str,
    registry: CryptoProviderRegistry | Mapping[str, Any] | None = None,
    ctx: Mapping[str, Any] | None = None,
    alg: str | None = None,
    tenant_id: Any = None,
) -> Any:
    row = await _key_for_operation(db, kid=kid, operation="verify", tenant_id=tenant_id)
    provider = _provider(row, registry=registry, ctx=ctx)
    return await provider.verify_signature(
        VerifySignatureRequest(
            payload=payload,
            signature=signature,
            key=public_material_from_row(row),
            alg=alg,
        )
    )


async def encrypt(
    db: Any,
    *,
    kid: str,
    plaintext: bytes,
    registry=None,
    ctx=None,
    alg: str | None = None,
) -> Any:
    row = await _key_for_operation(db, kid=kid, operation="encrypt")
    return await _provider(row, registry=registry, ctx=ctx).encrypt(
        EncryptRequest(plaintext=plaintext, key=provider_key_ref_from_row(row), alg=alg)
    )


async def decrypt(
    db: Any,
    *,
    kid: str,
    ciphertext: Any,
    registry=None,
    ctx=None,
    alg: str | None = None,
) -> bytes:
    row = await _key_for_operation(db, kid=kid, operation="decrypt")
    return await _provider(row, registry=registry, ctx=ctx).decrypt(
        DecryptRequest(
            ciphertext=ciphertext, key=provider_key_ref_from_row(row), alg=alg
        )
    )


async def wrap_key(
    db: Any,
    *,
    kid: str,
    material: bytes | Any,
    registry=None,
    ctx=None,
    alg: str | None = None,
) -> Any:
    row = await _key_for_operation(db, kid=kid, operation="wrap_key")
    return await _provider(row, registry=registry, ctx=ctx).wrap_key(
        WrapKeyRequest(
            material=material, wrapping_key=provider_key_ref_from_row(row), alg=alg
        )
    )


async def unwrap_key(
    db: Any, *, kid: str, wrapped: Any, registry=None, ctx=None, alg: str | None = None
) -> Any:
    row = await _key_for_operation(db, kid=kid, operation="unwrap_key")
    return await _provider(row, registry=registry, ctx=ctx).unwrap_key(
        UnwrapKeyRequest(
            wrapped=wrapped, wrapping_key=provider_key_ref_from_row(row), alg=alg
        )
    )


async def encapsulate(
    db: Any, *, kid: str, registry=None, ctx=None, alg: str | None = None
) -> Any:
    row = await _key_for_operation(db, kid=kid, operation="encapsulate")
    return await _provider(row, registry=registry, ctx=ctx).encapsulate(
        EncapsulateRequest(public_key=public_material_from_row(row), alg=alg)
    )


async def decapsulate(
    db: Any,
    *,
    kid: str,
    ciphertext: bytes | str,
    registry=None,
    ctx=None,
    alg: str | None = None,
) -> bytes:
    row = await _key_for_operation(db, kid=kid, operation="decapsulate")
    return await _provider(row, registry=registry, ctx=ctx).decapsulate(
        DecapsulateRequest(
            ciphertext=ciphertext, secret_key=provider_key_ref_from_row(row), alg=alg
        )
    )


async def attest_key(
    db: Any,
    *,
    kid: str,
    registry=None,
    ctx=None,
    claims: Mapping[str, Any] | None = None,
) -> Any:
    row = await _key_for_operation(db, kid=kid, operation="attest")
    return await _provider(row, registry=registry, ctx=ctx).attest_key(
        AttestKeyRequest(key=provider_key_ref_from_row(row), claims=claims or {})
    )


async def verify_attestation(
    db: Any, *, kid: str, evidence: Any, registry=None, ctx=None
) -> Any:
    row = await _key_for_operation(db, kid=kid, operation="verify_attestation")
    return await _provider(row, registry=registry, ctx=ctx).verify_attestation(
        VerifyAttestationRequest(
            evidence=evidence, trust_roots=(public_material_from_row(row),)
        )
    )


async def export_public(
    db: Any, *, kid: str, registry=None, ctx=None, format: str = "jwk"
) -> Any:
    row = await _key_for_operation(db, kid=kid, operation="export_public")
    provider = _provider(row, registry=registry, ctx=ctx)
    if hasattr(provider, "export_public_key"):
        return await provider.export_public_key(
            ExportPublicKeyRequest(key=public_material_from_row(row), format=format)
        )
    return public_material_from_row(row)


async def publish_jwks(
    db: Any, *, tenant_id: Any = None
) -> dict[str, list[dict[str, Any]]]:
    rows = await CryptoKey.list_active(
        tenant_id=tenant_id, db=db, operation="export_public"
    )
    return jwks_from_crypto_keys(rows)


__all__ = [
    "CryptoProviderRegistry",
    "attest_key",
    "create_key",
    "decapsulate",
    "decrypt",
    "encapsulate",
    "encrypt",
    "export_public",
    "publish_jwks",
    "rotate_key",
    "sign",
    "unwrap_key",
    "verify",
    "verify_attestation",
    "wrap_key",
]
