from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import httpx
import pytest


def _load_example_module(module_name: str, relative_path: str):
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.example
@pytest.mark.asyncio
async def test_device_authorization_falls_back_to_legacy_device_codes_endpoint() -> None:
    device_login = _load_example_module(
        "oauth_device_authorization_cli_example.device_login",
        "pkgs/110-examples/tba-example-oauth-device-authorization-cli/src/oauth_device_authorization_cli_example/device_login.py",
    )

    attempted: list[str] = []
    device_payload = {
        "device_code": "device-code-123",
        "user_code": "ABCD-EFGH",
        "verification_uri": "https://issuer.example/activate",
        "verification_uri_complete": "https://issuer.example/activate?user_code=ABCD-EFGH",
        "expires_in": 600,
        "interval": 5,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if (
            request.method == "GET"
            and request.url.path == "/.well-known/oauth-authorization-server"
        ):
            return httpx.Response(
                200,
                json={"issuer": "https://issuer.example"},
                request=request,
            )
        if request.method == "POST" and request.url.path == "/device_authorization":
            attempted.append(str(request.url))
            return httpx.Response(404, json={"detail": "not found"}, request=request)
        if (
            request.method == "POST"
            and request.url.path == "/device_codes/device_authorization"
        ):
            attempted.append(str(request.url))
            return httpx.Response(200, json=device_payload, request=request)
        return httpx.Response(404, json={"detail": "not found"}, request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport, base_url="https://issuer.example"
    ) as async_client:
        client = device_login.DeviceLoginClient(
            issuer="https://issuer.example",
            client_id="client-123",
            http_client=async_client,
        )
        device = await client.start()

    assert attempted == [
        "https://issuer.example/device_authorization",
        "https://issuer.example/device_codes/device_authorization",
    ]
    assert device.device_code == "device-code-123"
    assert device.user_code == "ABCD-EFGH"
    assert device.verification_uri == "https://issuer.example/activate"
    assert device.verification_uri_complete.endswith(device.user_code)
    assert device.expires_in == 600
    assert device.interval == 5
