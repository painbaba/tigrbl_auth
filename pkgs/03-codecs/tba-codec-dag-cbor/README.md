# tba-codec-dag-cbor

Use `encode` and `decode` for canonical DAG-CBOR. CID links use tag 42 and the binary identity prefix. Decoding rejects duplicate keys, trailing data and noncanonical encodings. Callers set message size limits and protocol constraints.

[Specification](https://ipld.io/specs/codecs/dag-cbor/spec/)
