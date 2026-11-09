"""Canonical SVID credential contracts."""

from dataclasses import dataclass
from tba_primitives_identity.enum_compat import StrEnum
from typing import Protocol

from .spiffe import SpiffeId


class SvidFormat(StrEnum):
    X509 = "x509-svid"
    JWT = "jwt-svid"


@dataclass(frozen=True, slots=True)
class Svid:
    spiffe_id: SpiffeId
    format: SvidFormat
    credential: bytes | str
    bundle_hint: str | None = None


class SvidProviderPort(Protocol):
    def fetch_svid(self, audience: str | None = None, /) -> Svid: ...


class SvidVerifierPort(Protocol):
    def verify_svid(self, svid: Svid, audience: str | None = None, /) -> SpiffeId: ...


__all__ = ["Svid", "SvidFormat", "SvidProviderPort", "SvidVerifierPort"]
