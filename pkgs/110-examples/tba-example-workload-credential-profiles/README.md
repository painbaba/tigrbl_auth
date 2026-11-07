# Workload credential profiles example

Runs structural WIT, WPT, and WIT-SVID validation. Production callers must additionally inject signature, key, trust, time, and replay verification.

## Run

From the repository checkout, sync the workspace — the example is a root
dependency and installs editable — then call `run_example`:

```shell
uv sync
uv run python -c "from workload_credential_profiles_example.main import run_example; print(run_example())"
```

The call returns `('wit', 'wit-svid', 'wpt')`, one label for each validated
credential profile.

