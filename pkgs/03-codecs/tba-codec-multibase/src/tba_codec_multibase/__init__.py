"""Multibase encoding and decoding for the base58btc alphabet."""

_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_DIGITS = {char: digit for digit, char in enumerate(_ALPHABET)}
_PREFIX = "z"


def encode_base58btc(data: bytes) -> str:
    """Encode bytes as a z-prefixed base58btc Multibase value."""
    number = int.from_bytes(data, "big")
    digits = []
    while number:
        number, digit = divmod(number, 58)
        digits.append(_ALPHABET[digit])
    zeros = len(data) - len(data.lstrip(b"\x00"))
    return _PREFIX + "1" * zeros + "".join(reversed(digits))


def decode_base58btc(text: str) -> bytes:
    """Decode a z-prefixed base58btc Multibase value or raise ValueError."""
    if not isinstance(text, str) or not text.startswith(_PREFIX):
        raise ValueError("expected a z-prefixed base58btc value")

    payload = text[1:]
    zeros = len(payload) - len(payload.lstrip("1"))
    number = 0
    try:
        for char in payload[zeros:]:
            number = number * 58 + _DIGITS[char]
    except KeyError as exc:
        raise ValueError("invalid base58btc character") from exc
    return b"\x00" * zeros + number.to_bytes((number.bit_length() + 7) // 8, "big")


__all__ = ["decode_base58btc", "encode_base58btc"]
