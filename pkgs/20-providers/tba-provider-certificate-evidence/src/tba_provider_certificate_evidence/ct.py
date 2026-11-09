from collections.abc import Iterable
from datetime import datetime
from hashlib import sha256

from asn1crypto import core
from asn1crypto import x509 as asn1_x509
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa

_SCT_LIST = "1.3.6.1.4.1.11129.2.4.2"
_LogKey = ec.EllipticCurvePublicKey | rsa.RSAPublicKey


class CtEvidenceUnavailable(ValueError):
    pass


def load_logs(public_keys: Iterable[bytes]) -> dict[bytes, _LogKey]:
    logs = {}
    for pem in public_keys:
        key = serialization.load_pem_public_key(pem)
        if not (
            (
                isinstance(key, ec.EllipticCurvePublicKey)
                and isinstance(key.curve, ec.SECP256R1)
            )
            or (isinstance(key, rsa.RSAPublicKey) and key.key_size >= 2048)
        ):
            raise ValueError("unsupported RFC 6962 CT log key")
        log_id = sha256(
            key.public_bytes(
                serialization.Encoding.DER,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        ).digest()
        logs[log_id] = key
    return logs


def _vector(data: bytes, offset: int) -> tuple[bytes, int]:
    if offset + 2 > len(data):
        raise ValueError("truncated SCT vector length")
    size = int.from_bytes(data[offset : offset + 2], "big")
    end = offset + 2 + size
    if end > len(data):
        raise ValueError("truncated SCT vector")
    return data[offset + 2 : end], end


def _signed_entry(
    leaf: x509.Certificate, issuer: x509.Certificate
) -> tuple[bytes, bytes]:
    tbs = asn1_x509.TbsCertificate.load(leaf.tbs_certificate_bytes, strict=True)
    extensions = tbs["extensions"]
    for index, extension in enumerate(extensions):
        if extension["extn_id"].dotted == _SCT_LIST:
            scts = core.OctetString.load(
                extension["extn_value"].contents, strict=True
            ).native
            del extensions[index]
            break
    else:
        raise ValueError("certificate is missing the embedded SCT extension")
    tbs_bytes = tbs.dump()
    issuer_key = asn1_x509.TbsCertificate.load(
        issuer.tbs_certificate_bytes, strict=True
    )["subject_public_key_info"].dump()
    return scts, sha256(issuer_key).digest() + len(tbs_bytes).to_bytes(
        3, "big"
    ) + tbs_bytes


def _verify_sct(sct: bytes, key: _LogKey, entry: bytes, at: datetime) -> bool:
    if len(sct) < 47 or sct[0] != 0:
        return False
    timestamp = sct[33:41]
    if int.from_bytes(timestamp, "big") > int(at.timestamp() * 1000):
        return False
    try:
        extensions, offset = _vector(sct, 41)
        signature, end = _vector(sct, offset + 2)
    except ValueError:
        return False
    if not signature or end != len(sct):
        return False
    payload = b"\x00\x00" + timestamp + b"\x00\x01" + entry
    payload += len(extensions).to_bytes(2, "big") + extensions
    try:
        if sct[offset : offset + 2] == b"\x04\x03" and isinstance(
            key, ec.EllipticCurvePublicKey
        ):
            key.verify(signature, payload, ec.ECDSA(hashes.SHA256()))
        elif sct[offset : offset + 2] == b"\x04\x01" and isinstance(
            key, rsa.RSAPublicKey
        ):
            key.verify(signature, payload, padding.PKCS1v15(), hashes.SHA256())
        else:
            return False
    except InvalidSignature:
        return False
    return True


def verify_transparency(
    leaf: x509.Certificate,
    issuer: x509.Certificate,
    logs: dict[bytes, _LogKey],
    at: datetime,
) -> None:
    data, entry = _signed_entry(leaf, issuer)
    entries, end = _vector(data, 0)
    if end != len(data) or not entries:
        raise ValueError("invalid embedded SCT list")
    offset = 0
    recognized = False
    verified = False
    while offset < len(entries):
        sct, offset = _vector(entries, offset)
        if not sct:
            raise ValueError("empty SCT entry")
        if sct[0] != 0:
            continue
        if len(sct) < 47:
            raise ValueError("truncated v1 SCT")
        key = logs.get(sct[1:33])
        if key is not None:
            recognized = True
            verified |= _verify_sct(sct, key, entry, at)
    if not recognized:
        raise CtEvidenceUnavailable("no embedded SCT uses a configured CT log")
    if not verified:
        raise ValueError("no trusted embedded SCT signature verified")
