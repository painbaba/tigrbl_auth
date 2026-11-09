"""RFC 8785 conformance tests for tba-codec-jcs."""

from __future__ import annotations

from decimal import Decimal

import pytest

from tba_codec_jcs import canonicalize, canonicalize_json


@pytest.mark.conformance
def test_rfc8785_sample_object_canonicalizes_to_expected_bytes() -> None:
    value = {
        "numbers": [333333333.33333329, 1e30, 4.50, 2e-3, 1e-27],
        "string": "\u20ac$\u000f\nA'\u0042\u0022\u005c\\\"/",
        "literals": [None, True, False],
    }

    assert canonicalize(value) == (
        '{"literals":[null,true,false],'
        '"numbers":[333333333.3333333,1e+30,4.5,0.002,1e-27],'
        '"string":"€$\\u000f\\nA\'B\\"\\\\\\\\\\"/"}'
    ).encode("utf-8")


@pytest.mark.conformance
def test_rfc8785_property_sorting_uses_raw_utf16_code_units() -> None:
    value = {
        "\u20ac": "Euro Sign",
        "\r": "Carriage Return",
        "\ufb33": "Hebrew Letter Dalet With Dagesh",
        "1": "One",
        "\U0001f600": "Emoji: Grinning Face",
        "\u0080": "Control",
        "\u00f6": "Latin Small Letter O With Diaeresis",
    }

    assert canonicalize(value).decode("utf-8") == (
        '{"\\r":"Carriage Return",'
        '"1":"One",'
        '"\u0080":"Control",'
        '"ö":"Latin Small Letter O With Diaeresis",'
        '"€":"Euro Sign",'
        '"😀":"Emoji: Grinning Face",'
        '"דּ":"Hebrew Letter Dalet With Dagesh"}'
    )


@pytest.mark.conformance
def test_rfc8785_parsed_json_rejects_duplicate_object_members() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        canonicalize_json('{"iss":"one","iss":"two"}')


@pytest.mark.conformance
def test_rfc8785_output_emits_no_whitespace_and_preserves_array_order() -> None:
    assert canonicalize({"z": [{"b": 2, "a": 1}], "a": [3, 2, 1]}) == (
        b'{"a":[3,2,1],"z":[{"a":1,"b":2}]}'
    )


@pytest.mark.conformance
def test_rfc8785_output_is_utf8_bytes_and_preserves_unicode_without_normalization() -> None:
    composed = "é"
    decomposed = "e\u0301"

    assert canonicalize({"v": composed}) == '{"v":"é"}'.encode("utf-8")
    assert canonicalize({"v": decomposed}) == '{"v":"e\u0301"}'.encode("utf-8")
    assert canonicalize({"v": composed}) != canonicalize({"v": decomposed})


@pytest.mark.conformance
@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_rfc8785_rejects_non_json_float_values(value: float) -> None:
    with pytest.raises(ValueError):
        canonicalize({"n": value})


@pytest.mark.conformance
def test_rfc8785_rejects_lone_surrogates_in_strings_and_member_names() -> None:
    with pytest.raises(ValueError):
        canonicalize({"v": "\udead"})
    with pytest.raises(ValueError):
        canonicalize({"\udead": "value"})


@pytest.mark.conformance
def test_rfc8785_rejects_numbers_that_are_not_safe_json_integers() -> None:
    with pytest.raises(ValueError):
        canonicalize({"n": 2**53})
    with pytest.raises(ValueError):
        canonicalize({"n": Decimal("1.23")})


@pytest.mark.conformance
def test_non_jcs_release_signing_helper_is_not_exported_as_jcs() -> None:
    import tba_auth.release_signing as release_signing

    assert hasattr(release_signing, "_canonical_json")
    assert not hasattr(release_signing, "canonicalize")
    assert not hasattr(release_signing, "canonicalize_json")
