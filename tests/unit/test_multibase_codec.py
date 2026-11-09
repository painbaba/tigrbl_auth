import pytest
from tba_codec_multibase import decode_base58btc, encode_base58btc


@pytest.mark.parametrize(
    ("data", "encoded"),
    [
        # draft-msporny-base58-02 section 5, with the Multibase prefix.
        (b"Hello World!", "z2NEpo7TZRRrLZSi2U"),
        (b"", "z"),
        (b"\x00\x00\x01", "z112"),
    ],
)
def test_base58btc_vectors(data, encoded):
    assert encode_base58btc(data) == encoded
    assert decode_base58btc(encoded) == data


@pytest.mark.parametrize("encoded", ["", "2NEpo7TZRRrLZSi2U", "Z112", "z0", "z 2"])
def test_invalid_base58btc(encoded):
    with pytest.raises(ValueError):
        decode_base58btc(encoded)
