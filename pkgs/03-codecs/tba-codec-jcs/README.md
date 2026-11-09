# tba-codec-jcs

Use `canonicalize` for JSON values or `canonicalize_json` for raw JSON. Both produce canonical UTF-8 bytes using the rfc8785 library. The raw JSON entry point rejects duplicate keys.

This package owns TBA’s strict JCS API. New callers should import from `tba_codec_jcs`.
The [RFC 8785 conformance suite](../../../tests/conformance/backlog/test_rfc8785_jcs.py) verifies this package.

[Specification](https://www.rfc-editor.org/rfc/rfc8785.html)
