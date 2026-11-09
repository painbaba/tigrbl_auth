# tba-provider-dns-txt

Typed DNS TXT lookup provider.

`DnsTxtResolver.lookup_txt(name)` performs an absolute TXT lookup with a
configurable lifetime. It joins the character strings within a single record,
preserves separate records as bytes, and distinguishes absent data from
temporary failures. Consumers can implement the `TxtResolver` protocol for
deterministic tests or another DNS backend. The shared contract lives in
`tba-contracts-dns` and is also exported here for existing callers.

```python
from tba_provider_dns_txt import DnsTxtResolver

answer = DnsTxtResolver(timeout=3).lookup_txt("_dmarc.example.com")
print(answer.status.value, answer.records)
```
