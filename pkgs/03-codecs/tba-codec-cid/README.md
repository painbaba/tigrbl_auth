# tba-codec-cid

Use `Cid.from_bytes` or `Cid.from_text` to parse a content identifier. The codec checks canonical unsigned varints and multihash length. Text support covers base58btc. Callers choose which codec, hash and digest length they trust.

[Specification](https://specs.ipfs.tech/cid/)
