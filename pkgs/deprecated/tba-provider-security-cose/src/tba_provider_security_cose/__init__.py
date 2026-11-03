"""Deprecated compatibility facade for split COSE ownership."""

from collections.abc import Callable, Mapping
import warnings

from tba_concrete_cose import (
    COSE_ALGORITHMS,
    CoseAlgorithm,
    CoseSign1Envelope,
    decode_cose_key,
    resolve_cose_algorithm,
)
from tba_provider_cose_cryptography import (
    load_cose_public_key,
    verify_detached_signature,
)

warnings.warn(
    "tba-provider-security-cose is deprecated; use tba-concrete-cose and "
    "tba-provider-cose-cryptography",
    DeprecationWarning,
    stacklevel=2,
)

CoseSigner = Callable[[bytes, Mapping[int | str, object], bytes], bytes]
CoseVerifier = Callable[[bytes, bytes, str], bool]


class CoseSign1Provider:
    """Compatibility coordinator retained until capability callers migrate."""

    def __init__(
        self, signer: CoseSigner | None = None, verifier: CoseVerifier | None = None
    ) -> None:
        self._signer = signer
        self._verifier = verifier

    def sign1(
        self,
        payload: bytes,
        protected_headers: Mapping[int | str, object],
        external_aad: bytes = b"",
    ) -> CoseSign1Envelope:
        if self._signer is None:
            raise RuntimeError("COSE signing backend is not configured")
        encoded = self._signer(payload, protected_headers, external_aad)
        return CoseSign1Envelope(encoded, payload, dict(protected_headers))

    def verify1(self, encoded: bytes, external_aad: bytes, profile: str) -> bool:
        if self._verifier is None:
            raise RuntimeError("COSE verification backend is not configured")
        if not encoded or not profile:
            raise ValueError("COSE verification requires message and profile")
        return self._verifier(encoded, external_aad, profile)


__all__ = [
    "COSE_ALGORITHMS",
    "CoseAlgorithm",
    "CoseSign1Envelope",
    "CoseSign1Provider",
    "CoseSigner",
    "CoseVerifier",
    "decode_cose_key",
    "load_cose_public_key",
    "resolve_cose_algorithm",
    "verify_detached_signature",
]
