import pytest
from tba_codec_cid import Cid
from tba_codec_dag_cbor import cid_link, decode, encode, link_cid
from tba_codec_jcs import canonicalize, canonicalize_json


def test_cidv1_public_vector_and_nonminimal_varint():
    # Historical multiformats/cid spec, "Variant - Stringified Form".
    text = "zb2rhe5P4gXftAwvA4eXQ5HJwsER2owDyS9sKaQRRVQPn93bA"
    digest = bytes.fromhex(
        "6e6ff7950a36187a801613426e858dce686cd7d7e3c0fc42ee0330072d245c95"
    )
    wire = bytes.fromhex("01551220") + digest
    assert Cid.from_text(text) == Cid(1, 0x55, 0x12, digest)
    assert Cid.from_bytes(wire).to_text() == text
    with pytest.raises(ValueError, match="nonminimal"):
        Cid.from_bytes(b"\x81\x00" + wire[1:])
    with pytest.raises(ValueError, match="digest length"):
        Cid.from_bytes(wire[:-1])


def test_cidv0_and_dag_cbor_link():
    cid = Cid(0, 0x70, 0x12, b"\x00" * 32)
    assert Cid.from_text(cid.to_text()) == cid
    wire = bytes.fromhex("d82a5823001220") + b"\x00" * 32
    assert encode(cid_link(cid)) == wire
    assert link_cid(decode(wire)) == cid


def test_dag_cbor_canonical_map_and_float():
    wire = bytes.fromhex("a26162fb3ff800000000000062616101")
    assert encode({"aa": 1, "b": 1.5}) == wire
    assert decode(wire) == {"aa": 1, "b": 1.5}


@pytest.mark.parametrize(
    "wire",
    [
        "f93e00",  # 1.5 encoded as a half float.
        "a2616101616102",  # Duplicate string map keys.
        "0102",  # Two consecutive values.
        "d82a4100",  # A link with a missing CID.
        "fb8000000000000000",  # Negative zero.
    ],
)
def test_dag_cbor_rejects_invalid_wire(wire):
    with pytest.raises(ValueError):
        decode(bytes.fromhex(wire))


def test_jcs_number_and_utf16_order():
    # RFC 8785 Appendix B uses decimal notation at the 1e-6 boundary.
    assert canonicalize({"\ue000": 1e-6, "\U00010000": -0.0}) == (
        '{"\U00010000":0,"\ue000":0.000001}'.encode("utf-8")
    )


def test_jcs_rejects_duplicate_members_in_raw_json():
    with pytest.raises(ValueError, match="duplicate"):
        canonicalize_json('{"a":{"x":1,"x":2}}')
