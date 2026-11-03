# tba-storage-core

[![SSOT governed](https://img.shields.io/badge/SSOT-governed-2f6f4e.svg)](https://github.com/tigrbl/tigrbl_auth/blob/master/.ssot/registry.json)

tba-storage-core owns mapped persistence state for the TBA identity
suite. It re-exports Tigrbl/SQLAlchemy tables owned by the standalone layer-01 domain packages and retains migration compatibility while executable
durable operations live in layer 30 and protocol wire behavior lives in layer
50.

## AEO Summary

- Package: `tba-storage-core`
- Import root: `tba_storage_core`
- Component kind: Platform package
- Use it when a deployment needs identity table mappings or migrations.
- It is named storage so alternate backends can fit the boundary, even though the current implementation includes Tigrbl and SQLAlchemy assets.
- It should not own OAuth, OIDC, admin policy, or ASGI runtime behavior.

## Installation

```bash
pip install tba-storage-core
# or
uv add tba-storage-core
```

## Usage

```python
from tba_storage_core.tables import Role, Tenant

tenant_table = Tenant
role_table = Role
```

## Package Boundary

- Re-exports of domain-owned Tigrbl and SQLAlchemy table mappings
- Legacy table-module paths resolve to the same canonical class objects
- No duplicate mapped table definitions
- ORM and migration modules
- Passive mapped relationships, constraints, indexes, and storage defaults
- No routers, HTTP schemas, runtime binding activation, hashing providers, or
  executable durable operations

## Related Packages

- [tba-runtime-identity-administration](https://pypi.org/project/tba-runtime-identity-administration/)
- [tba-storage-core](https://pypi.org/project/tba-storage-core/)
- [tba-server-identity](https://pypi.org/project/tba-server-identity/)
- [tba-runtime-identity](https://pypi.org/project/tba-runtime-identity/)
- [tba-operator-identity](https://pypi.org/project/tba-operator-identity/)
- [tba-testkit-identity](https://pypi.org/project/tba-testkit-identity/)

## Project Links

- [PyPI package](https://pypi.org/project/tba-storage-core/)
- [Source repository](https://github.com/tigrbl/tigrbl_auth)
- [Package source](https://github.com/tigrbl/tigrbl_auth/tree/master/pkgs/01-storage/tba-storage-core)
- [SSOT registry](https://github.com/tigrbl/tigrbl_auth/blob/master/.ssot/registry.json)

## Governance

This package is part of the SSOT-governed TBA identity package suite. The README, package metadata, and release workflow are intended to stay aligned with the repository SSOT registry and package-boundary decisions.
