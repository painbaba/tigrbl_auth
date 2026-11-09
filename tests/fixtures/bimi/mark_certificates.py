import base64
import gzip
from datetime import datetime, timedelta, timezone
from hashlib import sha256

from asn1crypto.core import OctetString
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

AT = datetime(2026, 10, 1, tzinfo=timezone.utc)
EKU = x509.ObjectIdentifier("1.3.6.1.5.5.7.3.31")
MARK_TYPE = x509.ObjectIdentifier("1.3.6.1.4.1.53087.1.13")
MARK_POLICY = x509.ObjectIdentifier("1.3.6.1.4.1.53087.1.1")
LOGOTYPE = x509.ObjectIdentifier("1.3.6.1.5.5.7.1.12")
SCT = x509.ObjectIdentifier("1.3.6.1.4.1.11129.2.4.2")
LEAF_CRL = "http://ca.example/leaf.crl"
ISSUER_CRL = "http://ca.example/issuer.crl"
SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" version="1.2" baseProfile="tiny-ps"'
    b' viewBox="0 0 16 16"><title>Example</title><rect width="16" height="16"/></svg>'
)


def _der(tag, data):
    length = len(data)
    if length < 128:
        return bytes((tag, length)) + data
    size = (length.bit_length() + 7) // 8
    return bytes((tag, 0x80 | size)) + length.to_bytes(size, "big") + data


def _logo(svg, *, corrupt_digest=False):
    def seq(data):
        return _der(0x30, data)

    digest = bytes(32) if corrupt_digest else sha256(svg).digest()
    sha256_oid = bytes.fromhex("0609608648016503040201")
    hashes_der = seq(seq(seq(sha256_oid) + _der(4, digest)))
    uri = b"data:image/svg+xml;base64," + base64.b64encode(gzip.compress(svg))
    details = seq(_der(0x16, b"image/svg+xml") + hashes_der + seq(_der(0x16, uri)))
    return seq(_der(0xA2, _der(0xA0, seq(seq(details)))))


def _key_usage(ca):
    return x509.KeyUsage(
        digital_signature=not ca,
        content_commitment=False,
        key_encipherment=False,
        data_encipherment=False,
        key_agreement=False,
        key_cert_sign=ca,
        crl_sign=ca,
        encipher_only=False,
        decipher_only=False,
    )


def _builder(name, key, issuer_name, issuer_key, *, ca=False, crl=None, eku=True):
    builder = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(issuer_name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(AT - timedelta(days=2))
        .not_valid_after(AT + timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca, None), critical=True)
        .add_extension(_key_usage(ca), critical=True)
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(key.public_key()), False
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(issuer_key.public_key()),
            False,
        )
    )
    if eku:
        builder = builder.add_extension(x509.ExtendedKeyUsage([EKU]), critical=False)
    if crl:
        point = x509.DistributionPoint(
            [x509.UniformResourceIdentifier(crl)], None, None, None
        )
        builder = builder.add_extension(
            x509.CRLDistributionPoints([point]), critical=False
        )
    return builder


def _signed_crl(name, key, *, serial=None, stale=False):
    end = AT - timedelta(hours=1) if stale else AT + timedelta(days=2)
    builder = (
        x509.CertificateRevocationListBuilder()
        .issuer_name(name)
        .last_update(AT - timedelta(days=1))
        .next_update(end)
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(key.public_key()), False
        )
    )
    if serial is not None:
        builder = builder.add_revoked_certificate(
            x509.RevokedCertificateBuilder()
            .serial_number(serial)
            .revocation_date(AT - timedelta(hours=2))
            .build()
        )
    return builder.sign(key, hashes.SHA256()).public_bytes(serialization.Encoding.DER)


def make_evidence(
    *,
    mark="Registered Mark",
    san="example.com",
    svg=SVG,
    corrupt_digest=False,
    corrupt_sct=False,
    revoke_leaf=False,
    revoke_issuer=False,
    stale=False,
    issuer_eku=True,
):
    root_key, issuer_key, leaf_key, log_key = (
        ec.generate_private_key(ec.SECP256R1()) for _ in range(4)
    )
    root_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Fixture Root")])
    issuer_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Fixture Issuer")])
    leaf_name = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, "Fixture Mark"),
            x509.NameAttribute(MARK_TYPE, mark),
        ]
    )
    root = _builder(root_name, root_key, root_name, root_key, ca=True, eku=False).sign(
        root_key, hashes.SHA256()
    )
    issuer = _builder(
        issuer_name,
        issuer_key,
        root_name,
        root_key,
        ca=True,
        crl=ISSUER_CRL,
        eku=issuer_eku,
    ).sign(root_key, hashes.SHA256())
    builder = (
        _builder(leaf_name, leaf_key, issuer_name, issuer_key, crl=LEAF_CRL)
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(san)]), critical=False)
        .add_extension(
            x509.CertificatePolicies([x509.PolicyInformation(MARK_POLICY, None)]), False
        )
        .add_extension(
            x509.UnrecognizedExtension(
                LOGOTYPE, _logo(svg, corrupt_digest=corrupt_digest)
            ),
            False,
        )
    )
    tbs = builder.sign(issuer_key, hashes.SHA256()).tbs_certificate_bytes
    issuer_der = issuer_key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    log_der = log_key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    stamp = int(AT.timestamp() * 1000).to_bytes(8, "big")
    payload = b"\x00\x00" + stamp + b"\x00\x01" + sha256(issuer_der).digest()
    payload += len(tbs).to_bytes(3, "big") + tbs + b"\x00\x00"
    signature = log_key.sign(payload, ec.ECDSA(hashes.SHA256()))
    if corrupt_sct:
        signature = signature[:-1] + bytes([signature[-1] ^ 1])
    sct = b"\x00" + sha256(log_der).digest() + stamp + b"\x00\x00\x04\x03"
    sct += len(signature).to_bytes(2, "big") + signature
    entry = len(sct).to_bytes(2, "big") + sct
    embedded = OctetString(len(entry).to_bytes(2, "big") + entry).dump()
    leaf = builder.add_extension(x509.UnrecognizedExtension(SCT, embedded), False).sign(
        issuer_key, hashes.SHA256()
    )
    crls = {
        LEAF_CRL: _signed_crl(
            issuer_name,
            issuer_key,
            serial=leaf.serial_number if revoke_leaf else None,
            stale=stale,
        ),
        ISSUER_CRL: _signed_crl(
            root_name, root_key, serial=issuer.serial_number if revoke_issuer else None
        ),
    }
    log_pem = log_key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return leaf, issuer, root, crls, log_pem
