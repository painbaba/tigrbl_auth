![Tigrbl Logo](https://raw.githubusercontent.com/swarmauri/swarmauri-sdk/master/assets/tigrbl_full_logo.png)

# tba_auth

Tigrbl-native authentication and authorization package for the Tigrbl ecosystem.

Active packages use the **TBA** namespace (`tba-*`, `tba_*`, and `@tba/*`).
See the [namespace migration guide](docs/packaging/tba-namespace-migration.md)
for import, environment, client, and legacy-package details.

## Repository state

This checkpoint is a **Step 12 final certification aggregation checkpoint with follow-up target/profile truth reconciliation and clean-room executor / validated-evidence contract hardening** layered on top of the earlier certification-target, clean-room-matrix, published-dependency, runtime-validation, test-graph, production-grade operator-control-plane, migration-portability, fail-closed-gates, and Tier 4 peer-program work.

The current repository truth is:

- `fully_certifiable_now = false`
- `fully_rfc_compliant_now = false`
- `strict_independent_claims_ready = false`
- `profile_scope_mismatch_set_empty = true`
- `alignment_only_checkpoint_no_new_certification_evidence = false`
- `clean_room_executor_matrix_declared_complete = true`
- `validated_manifest_identity_contract_installed = true`
- the package is **not yet certifiably fully featured**
- the package is **not yet certifiably fully RFC/spec compliant**

Final package-level certification is still blocked because the fail-closed validated execution gates remain incomplete for the clean-room runtime matrix, in-scope certification lanes, migration portability preservation, Tier 3 evidence rebuilt from validated runs, and preserved Tier 4 external peer bundles.

This update keeps the retained target/profile mismatch set empty for **RFC 7516**, **RFC 7592**, and **RFC 9207**, and it also hardens the preserved evidence model so runtime, test-lane, and migration manifests only count as passing when they carry identity, install-substrate linkage, environment identity, and the expected runtime / pytest / revision-aware backend artifacts.

Start with:

- `.ssot/specs/SPEC-1052-ssot-document-authority.yaml`
- `.ssot/registry.json`
- `docs/compliance/truth_chain.md`
- `docs/compliance/AUTHORITATIVE_CURRENT_DOCS.md`
- `CURRENT_STATE.md`
- `CERTIFICATION_STATUS.md`
- `docs/compliance/current_state_report.md`
- `docs/compliance/certification_state_report.md`
- `docs/compliance/release_gate_report.md`
- `docs/compliance/runtime_profile_report.md`
- `docs/compliance/validated_execution_report.md`
- `docs/compliance/PEER_MATRIX_REPORT.md`
- `docs/compliance/TIER4_PROMOTION_MATRIX.md`
- `docs/compliance/RELEASE_DECISION_RECORD.md`

Historical planning and scaffold-layout documents are retained under `docs/archive/` and are **non-authoritative** for the current repository state.

## Runtime entrypoints

- standalone gateway/application export: `tba_auth.gateway:app`
- application factory export: `tba_app_backend_public:app`
- plugin installation: `tba_auth.plugin:TbaPlugin`

## Current runtime model

The package is treated as an **ASGI 3 application package**, not as a single bundled server. Runtime-serving claims are separated into runner profiles. `Uvicorn`, `Hypercorn`, and `Tigrcorn` are declared as runner-qualified certification targets, and the `serve` operator can launch runtime **when** the selected runner profile is installed and the Tigrbl runtime stack is importable in the active environment.

## Tigrbl-only policy

This checkpoint remains intentionally aligned to Tigrbl guidance:

- prefer Tigrbl exports and Tigrbl type exports,
- use Tigrbl ops and surfaces rather than ad-hoc framework routes,
- avoid direct FastAPI or Starlette imports and dependencies in verified release scopes.

## Downstream implementation best practices

Downstream products should treat `tba_auth` as the owner of the identity
schema and product surfaces. A downstream authn/authz platform should compose
the app, plugin, split identity/authn/authz/protocol packages, and API/UIX front doors rather than
creating parallel tables for realms, tenants, principals, roles, sessions,
clients, tokens, or keys.

Use these boundaries:

- Schema and default rows belong in upstream TBA table packages. Tables
  such as `Realm` and `Tenant` use Tigrbl's `Bootstrappable` contract with
  `DEFAULT_ROWS`; the default superuser is created by the upstream admin
  bootstrap service.
- Downstream repositories may declare product-specific seed intent, but they
  should materialize it through upstream Tigrbl table/bootstrap abstractions or
  API/front-door operations. They should not introduce duplicate SQLAlchemy
  declarative bases or shadow identity tables.
- Runtime serving should select an explicit runner profile. For Tigrcorn-first
  deployments, install the `tigrcorn` extra and launch with
  `tba-auth serve --server tigrcorn` or the `tigrcorn` CLI against the
  downstream ASGI app.
- Keep provenance order: backend capability first, API front door second, UIX
  third. The platform-admin path is `tba-runtime-identity-administration` ->
  `tba-app-backend-platform-administration` -> `@tba/ui-platform-administration`; apply
  the same pattern to tenant-admin, developer, service-admin, public,
  my-account, and resource-validation surfaces.

## Installation profiles

### Base install

```bash
pip install .
```

### Storage extras

```bash
pip install '.[postgres]'
pip install '.[sqlite]'
```

### Runner extras

```bash
pip install '.[uvicorn]'
pip install '.[hypercorn]'
pip install '.[tigrcorn]'
pip install '.[servers]'
```

The `tigrcorn` extra is pinned to a published Tigrcorn runner package for Python `3.11` and `3.12`. Final certification is still blocked until preserved clean-room execution evidence exists for the full supported runtime/test/migration matrix and the Tier 4 external peer bundles are complete.

## Run

```bash
tba-auth claims lint
```

Launch the standalone app on Tigrcorn through `uv`:

```bash
uv run tba-auth serve --server tigrcorn --profile production --host 127.0.0.1 --port 8000 --no-require-tls
```

Or bring up the checked-in Docker example:

```bash
docker compose -f docker/docker-compose.yml up -d --build
```

The compose example publishes the service on `http://127.0.0.1:8001` to avoid
clobbering an existing local listener on `8000`.

## CLI device login consumer example

This repo includes a separate sample Python package at
`pkgs/110-examples/acme-notes-cli/`.
that demonstrates how another CLI can implement a `login` command on top of
`tba_auth` device authorization. The flow uses issuer discovery plus the
canonical `POST /device_authorization` and `POST /token` endpoints.

See `docs/examples/python-cli-device-login.md`.

or embed as a plugin:

```python
from tigrbl import TigrblApp
from tba_auth.plugin import TbaPlugin

app = TigrblApp()
plugin = TbaPlugin()
plugin.install(app)
```

## Notes

- OAuth 2.1 alignment is tracked as a profile, not as a formal RFC claim.
- `keys` is the canonical certified command family; `key` is no longer part of the certified operator surface.
- public "independent" wording remains disallowed until preserved Tier 4 external peer bundles exist and promote the retained boundary.
- The authoritative executable CLI surface is `pkgs/60-runtime/tba-cli-identity/src/tba_cli_identity/cli/metadata/` plus the generated `docs/reference/CLI_SURFACE.md`.
- A current checkpoint gap review remains published at `docs/compliance/PACKAGE_REVIEW_GAP_ANALYSIS.md`.
- Supplemental supporting review/plan docs remain available at `docs/compliance/INDEPENDENT_PACKAGE_REVIEW_2026-03-27.md` and `docs/compliance/CERTIFIABLE_DELIVERY_PLAN_2026-03-27.md`; the authoritative active document is the SSOT, and the generated reports and top-level current-state docs are its current projections.
- Dependency provenance for this checkpoint is preserved in `pyproject.toml`, `pkgs/60-runtime/tba-runtime-identity/pyproject.toml`, and `uv.lock`.

## Known current blockers

- preserved Tier 4 external peer bundles are still absent and `strict_independent_claims_ready` remains `false`
- the package is still **not** truthfully certifiably fully featured or fully RFC/spec compliant because the fail-closed validated execution gates remain red
- validated clean-room runtime matrix evidence is not yet fully preserved as passing
- validated in-scope certification lane evidence is not yet fully preserved as passing
- SQLite and PostgreSQL migration portability has not yet been preserved as passing in the final validated execution report
- Tier 3 evidence has not yet been explicitly rebuilt from validated-run manifests in a fully green final gate set
- the supported interpreter range remains Python `3.10`â€“`3.12`; this local checkpoint container only provides Python `3.13`, so it cannot truthfully generate the required preserved supported-matrix evidence by itself
- release bundles and attestation verification can be rebuilt from this checkpoint, but the result remains a final-release **candidate**, not a truthful final certification release

## License

Apache-2.0

## Clean-room certification matrix

Use `tox.ini` for the same profile commands locally and in CI.

Examples:

- `tox -e py310-base`
- `tox -e py311-sqlite-uvicorn`
- `tox -e py312-postgres-hypercorn`
- `tox -e py311-tigrcorn`
- `tox -e py312-devtest`
- `tox -e py311-gates`

The Tier 4 peer-execution handoff package for the full supported peer-profile set is emitted under `dist/tier4-external-handoff/`, but preserved independent external bundles are still absent in this checkpoint, so strict independent public claims remain blocked.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the prerequisites, the `uv` setup commands for a fresh clone, and one focused test to run first.
