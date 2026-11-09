"""Binary CIDv0 and CIDv1 with base58btc text representations."""

from dataclasses import dataclass

from tba_codec_multibase import decode_base58btc, encode_base58btc

_MAX_VARINT = 2**63 - 1
_V0_CODEC = 0x70  # dag-pb
_V0_HASH = 0x12  # sha2-256
_V0_PREFIX = bytes([_V0_HASH, 32])


def _varint(value: int) -> bytes:
    if type(value) is not int or not 0 <= value <= _MAX_VARINT:
        raise ValueError("CID fields require unsigned 63-bit integers")
    digits = bytearray()
    while value >= 128:
        digits.append((value & 0x7F) | 0x80)
        value >>= 7
    digits.append(value)
    return bytes(digits)


def _read_varint(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    for shift in range(0, 63, 7):
        if offset >= len(data):
            break
        digit = data[offset]
        offset += 1
        value |= (digit & 0x7F) << shift
        if digit < 128:
            if shift and digit == 0:
                raise ValueError("nonminimal CID varint")
            return value, offset
    raise ValueError("truncated or oversized CID varint")


@dataclass(frozen=True, slots=True)
class Cid:
    version: int
    codec: int
    hash_code: int
    digest: bytes

    def __post_init__(self) -> None:
        if type(self.version) is not int or self.version not in (0, 1):
            raise ValueError("unsupported CID version")
        _varint(self.codec)
        _varint(self.hash_code)
        if type(self.digest) is not bytes:
            raise ValueError("CID digest must be bytes")
        if self.version == 0 and (self.codec, self.hash_code, len(self.digest)) != (
            _V0_CODEC,
            _V0_HASH,
            32,
        ):
            raise ValueError("invalid CIDv0 multihash or codec")

    def to_bytes(self) -> bytes:
        multihash = _varint(self.hash_code) + _varint(len(self.digest)) + self.digest
        return (
            multihash
            if self.version == 0
            else b"\x01" + _varint(self.codec) + multihash
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "Cid":
        if type(data) is not bytes:
            raise ValueError("CID must be bytes")
        if len(data) == 34 and data.startswith(_V0_PREFIX):
            return cls(0, _V0_CODEC, _V0_HASH, data[2:])
        version, offset = _read_varint(data, 0)
        if version != 1:
            raise ValueError("unsupported CID version")
        codec, offset = _read_varint(data, offset)
        hash_code, offset = _read_varint(data, offset)
        size, offset = _read_varint(data, offset)
        if size != len(data) - offset:
            raise ValueError("CID multihash digest length mismatch")
        return cls(version, codec, hash_code, data[offset:])

    def to_text(self) -> str:
        text = encode_base58btc(self.to_bytes())
        return text[1:] if self.version == 0 else text

    @classmethod
    def from_text(cls, text: str) -> "Cid":
        if not isinstance(text, str):
            raise ValueError("CID text must be a string")
        legacy = len(text) == 46 and text.startswith("Qm")
        cid = cls.from_bytes(decode_base58btc("z" + text if legacy else text))
        if (cid.version == 0) != legacy:
            raise ValueError("CID version does not match its text representation")
        return cid


__all__ = ["Cid"]
