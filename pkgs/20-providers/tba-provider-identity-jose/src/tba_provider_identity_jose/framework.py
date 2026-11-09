"""Internal JOSE key and token primitives.

These types deliberately live in TBA.  They provide the bounded key
provider and JWT surface used by the identity runtime without importing an
external application framework.
"""

from __future__ import annotations

import base64
import json
import os
import secrets
import time
from dataclasses import dataclass, field
from tba_primitives_identity.enum_compat import StrEnum
from pathlib import Path
from typing import Any, Mapping

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, padding, rsa

from tba_primitives_identity.base64url import base64url_decode, base64url_encode


class JWAAlg(StrEnum):
    HS256 = "HS256"
    EDDSA = "EdDSA"
    RS256 = "RS256"


class KeyAlg(StrEnum):
    ED25519 = "Ed25519"
    RSA_PSS_SHA256 = "RSA_PSS_SHA256"


class KeyClass(StrEnum):
    asymmetric = "asymmetric"


class KeyUse(StrEnum):
    SIGN = "sign"
    VERIFY = "verify"


class ExportPolicy(StrEnum):
    SECRET_WHEN_ALLOWED = "secret_when_allowed"


@dataclass(frozen=True)
class KeySpec:
    klass: KeyClass
    alg: KeyAlg
    uses: tuple[KeyUse, ...]
    export_policy: ExportPolicy
    label: str = "jose_key"


@dataclass
class KeyReference:
    kid: str
    material: bytes | None
    public: bytes | None
    tags: dict[str, str] = field(default_factory=dict)


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value.encode("ascii"))


def _public_jwk(ref: KeyReference) -> dict[str, str]:
    public = serialization.load_pem_public_key(ref.public or b"")
    if isinstance(public, ed25519.Ed25519PublicKey):
        raw = public.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        return {"kty": "OKP", "crv": "Ed25519", "alg": "EdDSA", "use": "sig", "kid": ref.kid, "x": base64url_encode(raw)}
    if isinstance(public, rsa.RSAPublicKey):
        numbers = public.public_numbers()
        size = (numbers.n.bit_length() + 7) // 8
        exponent_size = (numbers.e.bit_length() + 7) // 8
        return {"kty": "RSA", "alg": "RS256", "use": "sig", "kid": ref.kid, "n": base64url_encode(numbers.n.to_bytes(size, "big")), "e": base64url_encode(numbers.e.to_bytes(exponent_size, "big"))}
    raise TypeError("unsupported JOSE public key")


class FileKeyProvider:
    """Small durable key provider for the JOSE runtime's signing keys."""

    def __init__(self, root: str | os.PathLike[str]):
        self.root = Path(root)

    def _path(self, kid: str) -> Path:
        safe = base64.urlsafe_b64encode(kid.encode()).decode().rstrip("=")
        return self.root / f"{safe}.jwk.json"

    async def create_key(self, spec: KeySpec) -> KeyReference:
        if spec.alg == KeyAlg.ED25519:
            private = ed25519.Ed25519PrivateKey.generate()
        elif spec.alg == KeyAlg.RSA_PSS_SHA256:
            private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        else:  # pragma: no cover - closed enum guard
            raise ValueError(f"unsupported JOSE key algorithm: {spec.alg}")
        private_pem = private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        public_pem = private.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        kid = f"{spec.label}:{secrets.token_hex(16)}"
        ref = KeyReference(kid, private_pem, public_pem, {"alg": spec.alg.value})
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(kid)
        path.write_text(json.dumps({"kid": kid, "material": _b64(private_pem), "public": _b64(public_pem), "tags": ref.tags}, sort_keys=True), encoding="utf-8")
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        return ref

    async def import_key(self, spec: KeySpec, material: bytes, *, public: bytes | None = None) -> KeyReference:
        private = serialization.load_pem_private_key(bytes(material), password=None) if bytes(material).startswith(b"-----BEGIN") else ed25519.Ed25519PrivateKey.from_private_bytes(bytes(material)[:32])
        public_pem = public or private.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        kid = f"{spec.label}:{secrets.token_hex(16)}"
        ref = KeyReference(kid, bytes(material), bytes(public_pem), {"alg": spec.alg.value})
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(kid)
        path.write_text(json.dumps({"kid": kid, "material": _b64(ref.material or b""), "public": _b64(ref.public or b""), "tags": ref.tags}, sort_keys=True), encoding="utf-8")
        return ref

    async def get_key(self, kid: str, *, include_secret: bool = False) -> KeyReference:
        payload = json.loads(self._path(kid).read_text(encoding="utf-8"))
        return KeyReference(str(payload["kid"]), _unb64(payload["material"]) if include_secret else None, _unb64(payload["public"]), dict(payload.get("tags") or {}))

    async def get_public_jwk(self, kid: str) -> dict[str, str]:
        return _public_jwk(await self.get_key(kid))

    async def jwks(self) -> dict[str, list[dict[str, str]]]:
        keys: list[dict[str, str]] = []
        if self.root.exists():
            for path in sorted(self.root.glob("*.jwk.json")):
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    keys.append(_public_jwk(KeyReference(str(payload["kid"]), None, _unb64(payload["public"]), dict(payload.get("tags") or {}))))
                except Exception:
                    continue
        return {"keys": keys}


class LocalKeyProvider(FileKeyProvider):
    def __init__(self) -> None:
        root = Path(os.getenv("TBA_JOSE_LOCAL_KEY_DIR", "runtime_secrets/local"))
        super().__init__(root / secrets.token_hex(16))


class JWTTokenService:
    def __init__(self, provider: FileKeyProvider):
        self.provider = provider

    async def mint(self, claims: Mapping[str, Any], *, alg: JWAAlg | str, kid: str, lifetime_s: int, subject: str | None = None, issuer: str | None = None, audience: Any = None) -> str:
        algorithm = JWAAlg(str(alg))
        now = int(time.time())
        payload = dict(claims)
        payload.setdefault("iat", now)
        payload.setdefault("exp", now + lifetime_s)
        if subject is not None: payload.setdefault("sub", subject)
        if issuer is not None: payload.setdefault("iss", issuer)
        if audience is not None: payload.setdefault("aud", audience)
        header_segment = base64url_encode(json.dumps({"alg": algorithm.value, "kid": kid, "typ": "JWT"}, separators=(",", ":")).encode())
        payload_segment = base64url_encode(json.dumps(payload, separators=(",", ":"), default=str).encode())
        signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
        ref = await self.provider.get_key(kid, include_secret=True)
        private = serialization.load_pem_private_key(ref.material or b"", password=None)
        if algorithm == JWAAlg.EDDSA and isinstance(private, ed25519.Ed25519PrivateKey):
            signature = private.sign(signing_input)
        elif algorithm == JWAAlg.RS256 and isinstance(private, rsa.RSAPrivateKey):
            signature = private.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
        else:
            raise ValueError(f"key {kid!r} is incompatible with {algorithm.value}")
        return f"{header_segment}.{payload_segment}.{base64url_encode(signature)}"

    async def verify(self, token: str, *, issuer: str | None = None, audience: Any = None) -> dict[str, Any]:
        try:
            header_segment, payload_segment, signature_segment = token.split(".")
            header = json.loads(base64url_decode(header_segment))
            payload = json.loads(base64url_decode(payload_segment))
            kid, algorithm = str(header["kid"]), JWAAlg(str(header["alg"]))
            ref = await self.provider.get_key(kid)
            public = serialization.load_pem_public_key(ref.public or b"")
            signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
            signature = base64url_decode(signature_segment)
            if algorithm == JWAAlg.EDDSA and isinstance(public, ed25519.Ed25519PublicKey):
                public.verify(signature, signing_input)
            elif algorithm == JWAAlg.RS256 and isinstance(public, rsa.RSAPublicKey):
                public.verify(signature, signing_input, padding.PKCS1v15(), hashes.SHA256())
            else:
                raise ValueError("JWT key and algorithm do not match")
        except Exception as exc:
            raise ValueError("JWT signature verification failed") from exc
        if issuer is not None and payload.get("iss") != issuer:
            raise ValueError("JWT issuer mismatch")
        if audience is not None:
            expected = {audience} if isinstance(audience, str) else set(audience)
            actual_value = payload.get("aud")
            actual = {actual_value} if isinstance(actual_value, str) else set(actual_value or ())
            if not expected.intersection(actual):
                raise ValueError("JWT audience mismatch")
        return payload


__all__ = ["ExportPolicy", "FileKeyProvider", "JWAAlg", "JWTTokenService", "KeyAlg", "KeyClass", "KeyReference", "KeySpec", "KeyUse", "LocalKeyProvider"]
