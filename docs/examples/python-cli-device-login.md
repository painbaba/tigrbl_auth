# Python CLI Device Login Against `tba_auth`

This repository exposes the server-side pieces needed for RFC 8628 device authorization:

- `POST /device_authorization`
- `POST /token` with `grant_type=urn:ietf:params:oauth:grant-type:device_code`
- discovery metadata at `/.well-known/oauth-authorization-server`

The sample consumer package under `pkgs/110-examples/tba-example-oauth-device-authorization-cli/` shows how a different Python package can expose a `login` command and use that flow for CLI authentication.

## What the consumer package does

1. Fetch issuer metadata from `/.well-known/oauth-authorization-server`.
2. Read `device_authorization_endpoint` and `token_endpoint` when present.
3. Fall back to `{issuer}/device_authorization` and `{issuer}/token` when the active profile does not publish device metadata.
4. For compatibility with this repository's older runtime shape, also try `{issuer}/device_codes/device_authorization` if the canonical device endpoint is not mounted.
5. Request a device code with its own `client_id`.
6. Print `verification_uri_complete` and `user_code` for the operator.
7. Poll the token endpoint until the device is approved.
8. Cache the returned tokens locally.

## Consumer package shape

```text
pkgs/110-examples/tba-example-oauth-device-authorization-cli/
  pyproject.toml
  src/oauth_device_authorization_cli_example/main.py
  src/oauth_device_authorization_cli_example/device_login.py
```

## Example `login` command

The package registers the `oauth-device-login` console script (`oauth-device-login --help` lists the
`login` subcommand):

```bash
oauth-device-login login \
  --issuer https://authn.example.com \
  --client-id 7b7075b1-9d4b-4f7f-93a0-cf2994df44d9 \
  --scope "openid profile email"
```

## Minimal integration contract

The consumer package only needs:

- an issuer URL
- a pre-registered client ID
- an HTTP client

It does not need to import `tba_auth` directly in production. It only talks to:

- `GET /.well-known/oauth-authorization-server`
- `POST /device_authorization`
- `POST /token`

## Notes about this repository

In this repository, approval is exercised in tests through the `approve_device_code` helper. In a real deployment, the approval step is performed by the user visiting the verification URI and authenticating through the issuer's browser-facing surface.
