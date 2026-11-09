"""Restricted RFC 9421 HTTP message signatures for ZCAP-LD invocations."""

import base64
import binascii
import gzip
import json
import re
import zlib
from dataclasses import dataclass
from hashlib import sha256

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from tba_codec_jcs import canonicalize

from .schemas import (
    ACTION,
    ZcapError,
    ZcapHttpInvocation,
    ZcapRoot,
    validate_target,
    validate_uri,
)

_MAX_HEADER = 16 * 1024
_MAX_DOCUMENT = 64 * 1024
_MAX_BODY = 1024 * 1024
_LABEL = "zcap"
_REQUIRED = ("@method", "@target-uri", "capability-invocation", "content-digest")
_NONCE = re.compile(r"[A-Za-z0-9_-]{16,128}")
_CONTENT_TYPE = re.compile(r"[a-z0-9.+-]+/[a-z0-9.+-]+")
_METHOD = re.compile(r"[A-Z]{1,16}")
_PARAMS = re.compile(
    r"^zcap=(\([^)]+\));created=(0|[1-9][0-9]{0,11});expires=(0|[1-9][0-9]{0,11})"
    r';nonce="([A-Za-z0-9_-]{16,128})";keyid="([^"\\]+)";alg="ed25519"$'
)
_CAPABILITY = re.compile(
    r'^zcap (?:id="([^"]+)"|capability=([A-Za-z0-9_-]+)),action="([^"]+)"$'
)


@dataclass(frozen=True, slots=True)
class InvocationSignature:
    capability: str | dict
    action: str
    key_id: str
    created: int
    expires: int
    nonce: str
    signature: bytes
    signing_input: bytes


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _digest(body: bytes) -> str:
    if type(body) is not bytes or len(body) > _MAX_BODY:
        raise ZcapError("expected a bounded request body")
    return "sha-256=:" + _b64(sha256(body).digest()) + ":"


def _components(content_type: str | None) -> str:
    fields = _REQUIRED
    if content_type is not None:
        if not _CONTENT_TYPE.fullmatch(content_type):
            raise ZcapError("unsupported signed content type")
        fields += ("content-type",)
    return "(" + " ".join(f'"{field}"' for field in fields) + ")"


def _signature_base(
    method: str,
    target: str,
    capability: str,
    digest: str,
    content_type: str | None,
    params: str,
) -> bytes:
    validate_target(target)
    if not isinstance(method, str) or not _METHOD.fullmatch(method):
        raise ZcapError("unsupported HTTP method")
    lines = [
        f'"@method": {method}',
        f'"@target-uri": {target}',
        f'"capability-invocation": {capability}',
        f'"content-digest": {digest}',
    ]
    if content_type is not None:
        lines.append(f'"content-type": {content_type}')
    lines.append(f'"@signature-params": {params}')
    return "\n".join(lines).encode("ascii")


def _capability_header(capability: ZcapRoot | dict, action: str) -> str:
    if not isinstance(action, str) or not ACTION.fullmatch(action):
        raise ZcapError("invalid capability action")
    if isinstance(capability, ZcapRoot):
        value = f'id="{capability.id}"'
    else:
        try:
            document = canonicalize(capability)
        except (ValueError, RecursionError) as exc:
            raise ZcapError("cannot encode delegated capability") from exc
        if len(document) > _MAX_DOCUMENT:
            raise ZcapError("delegated capability exceeds the document limit")
        encoded = base64.urlsafe_b64encode(gzip.compress(document, mtime=0))
        value = "capability=" + encoded.decode("ascii").rstrip("=")
    header = f'zcap {value},action="{action}"'
    if len(header) > _MAX_HEADER:
        raise ZcapError("capability invocation header exceeds the profile limit")
    return header


def sign_http_invocation(
    capability: ZcapRoot | dict,
    *,
    method: str,
    target: str,
    action: str,
    key_id: str,
    key: Ed25519PrivateKey,
    created: int,
    expires: int,
    nonce: str,
    body: bytes = b"",
    content_type: str | None = None,
) -> ZcapHttpInvocation:
    validate_uri(key_id)
    if (
        type(created) is not int
        or type(expires) is not int
        or not 0 <= created < expires <= 999999999999
        or not isinstance(nonce, str)
        or not _NONCE.fullmatch(nonce)
    ):
        raise ZcapError("invalid HTTP signature times or nonce")
    if body and content_type is None:
        raise ZcapError("request body requires a signed content type")
    capability_header = _capability_header(capability, action)
    digest = _digest(body)
    params = (
        f"{_components(content_type)};created={created};expires={expires}"
        f';nonce="{nonce}";keyid="{key_id}";alg="ed25519"'
    )
    data = _signature_base(
        method, target, capability_header, digest, content_type, params
    )
    headers = (
        ("capability-invocation", capability_header),
        ("content-digest", digest),
        ("signature-input", f"{_LABEL}={params}"),
        ("signature", f"{_LABEL}=:{_b64(key.sign(data))}:"),
    )
    if content_type is not None:
        headers += (("content-type", content_type),)
    return ZcapHttpInvocation(method, target, headers, body)


def _unique_pairs(pairs: list) -> dict:
    result = {}
    for name, value in pairs:
        if name in result:
            raise ZcapError("duplicate capability JSON field")
        result[name] = value
    return result


def _unpack_capability(encoded: str) -> dict:
    try:
        compressed = base64.b64decode(
            encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True
        )
        inflater = zlib.decompressobj(wbits=31)
        document = inflater.decompress(compressed, _MAX_DOCUMENT + 1)
        if len(document) > _MAX_DOCUMENT or not inflater.eof or inflater.unused_data:
            raise ZcapError("invalid or oversized compressed capability")
        value = json.loads(document.decode("utf-8"), object_pairs_hook=_unique_pairs)
    except (ValueError, zlib.error, RecursionError) as exc:
        raise ZcapError("invalid encoded capability") from exc
    if not isinstance(value, dict):
        raise ZcapError("expected a delegated capability object")
    return value


def read_invocation_signature(request: ZcapHttpInvocation) -> InvocationSignature:
    protected = {
        "capability-invocation",
        "content-digest",
        "signature-input",
        "signature",
        "content-type",
        "content-encoding",
    }
    headers = {}
    for name, value in request.headers:
        name = name.lower()
        if name not in protected:
            continue
        if name in headers or not re.fullmatch(r"[ -~]{1,16384}", value):
            raise ZcapError("duplicate or invalid signature field")
        headers[name] = value.strip(" ")
    if "content-encoding" in headers:
        raise ZcapError("encoded HTTP content is outside this profile")
    cap_header = headers.get("capability-invocation", "")
    cap = _CAPABILITY.fullmatch(cap_header)
    sig_input = headers.get("signature-input", "")
    params = _PARAMS.fullmatch(sig_input)
    content_type = headers.get("content-type")
    if not cap or not params or params[1] != _components(content_type):
        raise ZcapError("unexpected invocation or signature profile")
    if request.body and content_type is None:
        raise ZcapError("request body requires a signed content type")
    digest = _digest(request.body)
    if headers.get("content-digest") != digest:
        raise ZcapError("request body digest mismatch")
    sig_header = headers.get("signature", "")
    match = re.fullmatch(r"zcap=:([A-Za-z0-9+/]{86}==):", sig_header)
    if not match:
        raise ZcapError("invalid HTTP signature encoding")
    try:
        signature = base64.b64decode(match[1], validate=True)
    except binascii.Error as exc:
        raise ZcapError("invalid HTTP signature encoding") from exc
    if _b64(signature) != match[1]:
        raise ZcapError("noncanonical HTTP signature encoding")
    root_id, compressed, action = cap.groups()
    key_id = params[5]
    validate_uri(key_id)
    if not ACTION.fullmatch(action):
        raise ZcapError("invalid capability action")
    if root_id is not None:
        validate_uri(root_id)
    return InvocationSignature(
        root_id if root_id is not None else _unpack_capability(compressed),
        action,
        key_id,
        int(params[2]),
        int(params[3]),
        params[4],
        signature,
        _signature_base(
            request.method,
            request.target,
            cap_header,
            digest,
            content_type,
            sig_input[len(_LABEL) + 1 :],
        ),
    )
