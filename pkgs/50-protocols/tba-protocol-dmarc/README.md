# tba-protocol-dmarc

DMARC TXT record parsing, DNS discovery and policy selection.

`parse_policy_record` returns the policy, subdomain policy, testing flag, and
other fields used in policy selection. `discover_policy` walks the DNS tree
using an injected resolver and reports the effective policy and its source.
Supply `author_exists=False` when the caller has established that the author
domain is nonexistent and needs `np` handling.

```python
from tba_protocol_dmarc import discover_policy

result = discover_policy(dns, "mail.example.com")
print(result.status.value, result.policy_source, result.effective_policy)
```

This package selects published policy. It does not perform per-message SPF
or DKIM authentication.
