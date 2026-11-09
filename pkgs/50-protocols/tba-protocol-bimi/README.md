# tba-protocol-bimi

BIMI TXT record parsing and selector discovery.

Use `parse_assertion` to inspect a known record or `discover_assertion` to
look up a selector at the author domain and, if the record is absent, its
organizational domain. Discovery returns the actual assertion owner.

```python
from tba_protocol_bimi import discover_assertion
from tba_protocol_dmarc import discover_policy

policy = discover_policy(dns, "mail.example.com")
result = discover_assertion(
    dns, "mail.example.com", organizational_domain=policy.organizational_domain
)
```

These functions perform domain-level discovery. The layer-55 BIMI profile
evaluates DMARC eligibility and Mark Certificate evidence.
