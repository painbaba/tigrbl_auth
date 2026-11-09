# tba-codec-multibase

Dependency-free Python codec for base58btc Multibase values. Use
`encode_base58btc(bytes)` and `decode_base58btc(str)`. Both functions handle
the lowercase `z` prefix and preserve leading zero bytes.

The codec converts bytes and text. Its callers set input size limits for
untrusted data and validate decoded values according to their protocols.

See the [Multibase registry](https://github.com/multiformats/multibase)
and [Base58 test vectors](https://datatracker.ietf.org/doc/html/draft-msporny-base58-02#section-5).
