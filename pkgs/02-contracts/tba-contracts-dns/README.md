# tba-contracts-dns

DNS TXT lookup contracts and shared TXT record handling.

`TxtResolver`, `TxtResult`, and `TxtStatus` let protocol consumers accept a
resolver without a DNS transport dependency. `normalize_domain` canonicalizes
domain names for lookup. `versioned_records` and `parse_tags` handle the shared
TXT tag-list shape used by BIMI and DMARC.

```python
from tba_contracts_dns import TxtResult, TxtStatus


class StaticDns:
    def lookup_txt(self, name: str) -> TxtResult:
        if name == "_dmarc.example.com":
            return TxtResult(TxtStatus.FOUND, (b"v=DMARC1; p=reject",))
        return TxtResult(TxtStatus.ABSENT)
```
