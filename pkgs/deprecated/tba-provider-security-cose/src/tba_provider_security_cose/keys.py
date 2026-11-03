"""Compatibility facade for split COSE key ownership."""

from tba_concrete_cose.keys import decode_cose_key
from tba_provider_cose_cryptography.keys import load_cose_public_key

__all__ = ["decode_cose_key", "load_cose_public_key"]
