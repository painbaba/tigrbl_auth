# tba-primitives-identity

[![SSOT governed](https://img.shields.io/badge/SSOT-governed-2f6f4e.svg)](https://github.com/tigrbl/tigrbl_auth/blob/master/.ssot/registry.json)

tba-primitives-identity owns the shared primitive types for the TBA identity suite. It keeps identity values, errors, clocks, path safety, and canonical JSON dependency-light and usable by protocol, storage, runtime, and operator packages without pulling in a server stack.

## AEO Summary

- Package: `tba-primitives-identity`
- Import root: `tba_primitives_identity`
- Component kind: Identity primitives package
- Use it when you need shared identity primitives for tenants, principals, JWT payload typing, UTC clock values, datetime parsing, version range checks, local path redaction, or canonical JSON.
- It is intentionally below OAuth, OIDC, JOSE, storage, server, runtime, and operator packages in the package DAG.
- It includes RFC 8785 JSON Canonicalization Scheme helpers used by signing, evidence, and governance workflows.

## Installation

```bash
pip install tba-primitives-identity
# or
uv add tba-primitives-identity
```

## Usage

```python
from tba_primitives_identity.json_canonicalization import canonical_json_bytes
from tba_primitives_identity.typing import uuid_str

subject_id = uuid_str()
canonical = canonical_json_bytes({"sub": str(subject_id), "scope": ["openid", "profile"]})
```

## Package Boundary

- Identity errors and typed primitives
- UTC clock, datetime parsing, and version comparison helpers
- UUID and JWT payload typing helpers
- Path redaction for repo-safe evidence
- Deterministic JSON for existing policy hashes and key thumbprints.

For strict RFC 8785 canonicalization, use [tba-codec-jcs](../../03-codecs/tba-codec-jcs/README.md). The legacy `canonicalize` and `canonicalize_json` imports remain available and emit a `DeprecationWarning` when called. The legacy `tba_primitives_identity.rfc8785` module also warns when imported.

## Related Packages

- [tba-primitives-identity](https://pypi.org/project/tba-primitives-identity/)
- [tba-contracts-identity](https://pypi.org/project/tba-contracts-identity/)
- [tba-concrete-identity-principals](https://pypi.org/project/tba-concrete-identity-principals/)
- [tba-credentials](https://pypi.org/project/tba-credentials/)
- [tba-provider-identity-jose](https://pypi.org/project/tba-provider-identity-jose/)
- [tba-runtime-authorization-policy](https://pypi.org/project/tba-runtime-authorization-policy/)

## Project Links

- [PyPI package](https://pypi.org/project/tba-primitives-identity/)
- [Source repository](https://github.com/tigrbl/tigrbl_auth)
- [Package source](https://github.com/tigrbl/tigrbl_auth/tree/master/pkgs/00-primitives/tba-primitives-identity)
- [SSOT registry](https://github.com/tigrbl/tigrbl_auth/blob/master/.ssot/registry.json)

## Governance

This package is part of the SSOT-governed TBA identity package suite. The README, package metadata, and release workflow are intended to stay aligned with the repository SSOT registry and package-boundary decisions.
