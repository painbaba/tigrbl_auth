# Contributing

This quickstart sets up the repository from a fresh clone and runs one
focused check.

## Prerequisites

- `git`
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/) — this
  repository mandates `uv` for Python and package execution; see `AGENT.md`.
- Python `3.12` for this quickstart (`uv` can provision it).

## Clone

```shell
git clone https://github.com/tigrbl/tigrbl_auth.git
cd tigrbl_auth
```

## Set up the environment

From the repository root:

```shell
uv sync --locked --python 3.12
```

This creates `.venv/` and installs the workspace packages in editable mode.
uv fetches the pinned Tigrbl dependencies from Git.

## Run a focused check

```shell
uv run --locked --python 3.12 pytest tests/unit/test_account_self_service_capability.py -q
```

This should report `4 passed`.

## Broader checks

`tox.ini` defines the certification and test profiles used locally and in CI,
for example `uv run tox -e py311-devtest` or `uv run tox -e py311-test-core`. Agents should
also read `AGENT.md` for the `ssot-registry` and `uv` invocation policy that
governs repository changes.
