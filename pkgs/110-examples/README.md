# Layer 110: Examples

This terminal layer owns runnable demonstration and sample-consumer packages.
Examples may compose stable public production packages to show complete usage,
but they must not become canonical implementation owners or depend on test-only
packages.

Current packages:

- [`tba-example-oauth-device-authorization-cli`](./tba-example-oauth-device-authorization-cli/README.md)
  — a runnable CLI consumer that performs an OAuth 2.0 device authorization
  grant against a TBA deployment.
- [`tba-example-workload-credential-profiles`](./tba-example-workload-credential-profiles/README.md)
  — a runnable structural validation pass over the WIT, WPT, and WIT-SVID
  workload credential profiles.
