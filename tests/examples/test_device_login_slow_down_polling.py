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
async def test_poll_for_tokens_raises_interval_after_slow_down_and_returns_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    device_login = _load_example_module(
        "oauth_device_authorization_cli_example.device_login",
        "pkgs/110-examples/tba-example-oauth-device-authorization-cli/src/oauth_device_authorization_cli_example/device_login.py",
    )

    token_payload = {
        "access_token": "access-token-123",
        "refresh_token": "refresh-token-456",
        "token_type": "bearer",
    }
    token_responses: list[tuple[int, dict]] = [
        (400, {"error": "authorization_pending"}),
        (400, {"error": "slow_down"}),
        (200, token_payload),
    ]
    token_requests: list[str] = []

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
        if request.method == "POST" and request.url.path == "/token":
            token_requests.append(str(request.url))
            status, payload = token_responses.pop(0)
            return httpx.Response(status, json=payload, request=request)
        return httpx.Response(404, json={"detail": "not found"}, request=request)

    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr(device_login.asyncio, "sleep", fake_sleep)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport, base_url="https://issuer.example"
    ) as async_client:
        client = device_login.DeviceLoginClient(
            issuer="https://issuer.example",
            client_id="client-123",
            http_client=async_client,
        )
        tokens = await client.poll_for_tokens(
            "device-code-123",
            interval=3,
            expires_in=600,
        )

    assert token_requests == [
        "https://issuer.example/token",
        "https://issuer.example/token",
        "https://issuer.example/token",
    ]
    assert sleeps == [3, 8]
    assert sleeps[1] == sleeps[0] + 5
    assert tokens == token_payload
