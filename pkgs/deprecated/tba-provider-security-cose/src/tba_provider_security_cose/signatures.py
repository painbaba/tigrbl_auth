"""Compatibility facade for the cryptography-backed COSE provider."""

from tba_provider_cose_cryptography.signatures import verify_detached_signature

__all__ = ["verify_detached_signature"]
