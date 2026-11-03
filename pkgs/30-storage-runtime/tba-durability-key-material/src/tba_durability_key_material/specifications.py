"""Crypto-key aliases and executable persistence specifications."""

from tba_storage_key_material.tables import CryptoKey, CryptoKeyVersion

from tigrbl import deriveTableSpec
from tba_durability_key_material.hooks import CRYPTO_KEY_RUNTIME_HOOKS


CryptoKeyTable = CryptoKey
CryptoKeyVersionTable = CryptoKeyVersion

CryptoKeyRuntimeSpec = deriveTableSpec(
    CryptoKeyTable,
    hooks=CRYPTO_KEY_RUNTIME_HOOKS,
)
CryptoKeyVersionRuntimeSpec = deriveTableSpec(CryptoKeyVersionTable)


__all__ = [
    "CryptoKeyRuntimeSpec",
    "CryptoKeyTable",
    "CryptoKeyVersionRuntimeSpec",
    "CryptoKeyVersionTable",
]
