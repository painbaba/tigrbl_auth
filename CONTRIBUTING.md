# Contributing

This quickstart sets up the repository from a fresh clone and runs one
focused check.

## Prerequisites

- `git`
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/) — this
  repository mandates `uv` for Python and package execution; see `AGENT.md`.
- Python `3.10` through `3.15` (`uv` can provision the interpreter itself).

## Clone

```shell
git clone https://github.com/tigrbl/tigrbl_auth.git
cd tigrbl_auth
```

## Sibling `tigrbl` checkout

The lockfile resolves `tigrbl-migrations` from an editable checkout at
`../tigrbl` relative to this repository, so a sibling clone of the `tigrbl`
repository at the pinned revision is required before syncing:

```shell
git clone https://github.com/tigrbl/tigrbl.git ../tigrbl
git -C ../tigrbl checkout a2fb7b54042f94a131ac4b1e0092c1e9bdfe0421
```

## Set up the environment

From the repository root:

```shell
uv sync
```

This creates `.venv/` and installs the workspace packages editable.

## Run a focused check

```shell
uv run pytest tests/unit/test_account_self_service_capability.py -q
```

This should report `4 passed`.

## Broader checks

`tox.ini` defines the certification and test profiles used locally and in CI,
for example `tox -e py311-devtest` or `tox -e py311-test-core`. Agents should
also read `AGENT.md` for the `ssot-registry` and `uv` invocation policy that
governs repository changes.
