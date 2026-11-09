# tba-provider-certificate-evidence

X.509 path, CRL, and RFC 6962 SCT verification.

Supply parsed certificates, explicit trust anchors, a timezone-aware
verification time, and evidence from your deployment. `verify_chain` returns
the selected chain in leaf-first order. Passing CRLs enables chain-wide
revocation checking. `load_crls` checks signed CRL freshness and
`verify_transparency` verifies embedded SCTs against configured log keys.

```python
from tba_provider_certificate_evidence import (
    load_crls,
    load_logs,
    verify_chain,
    verify_transparency,
)

chain = verify_chain(leaf, intermediates, roots, at)
crls = load_crls(chain, local_crls_by_url.get, at)
verify_chain(leaf, chain[1:-1], chain[-1:], at, crls)
verify_transparency(chain[0], chain[1], load_logs(ct_public_keys_pem), at)
```

The caller supplies the CRL source. The provider does not fetch distribution
point URLs or decide which anchors and logs are appropriate for a profile.
