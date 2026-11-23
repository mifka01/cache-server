from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Any, Callable

import pytest


def _basic_auth(token: str) -> str:
    credentials = base64.b64encode(f":{token}".encode()).decode()
    return f"Authorization: Basic {credentials}"


def _forge_hs256(payload: dict[str, str], key: str) -> str:
    """HS256 JWT built exactly like PyJWT does (sorted header, compact JSON)."""

    def b64(data: bytes) -> bytes:
        return base64.urlsafe_b64encode(data).rstrip(b"=")

    header = b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = b64(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = header + b"." + body
    signature = b64(hmac.new(key.encode(), signing_input, hashlib.sha256).digest())
    return (signing_input + b"." + signature).decode()


@pytest.mark.security
def test_private_cache_metadata_requires_token(
    require_api_endpoint: None,
    http_request: Callable[..., tuple[int, str]],
    api_base_url: str,
    private_cache_name: str,
) -> None:
    del require_api_endpoint
    status, body = http_request(f"{api_base_url}/api/v1/cache/{private_cache_name}?")
    assert status == 401
    assert "publicSigningKeys" not in body


@pytest.mark.security
def test_private_cache_metadata_rejects_invalid_token(
    require_api_endpoint: None,
    http_request: Callable[..., tuple[int, str]],
    api_base_url: str,
    private_cache_name: str,
) -> None:
    del require_api_endpoint
    status, body = http_request(
        f"{api_base_url}/api/v1/cache/{private_cache_name}?",
        headers=["Authorization: Bearer invalid-token"],
    )
    assert status == 401
    assert "publicSigningKeys" not in body


@pytest.mark.security
def test_private_cache_metadata_accepts_valid_token(
    require_api_endpoint: None,
    request_json: Callable[..., tuple[int, Any]],
    api_base_url: str,
    private_cache_name: str,
    private_cache_token: str,
) -> None:
    del require_api_endpoint
    status, payload = request_json(
        f"{api_base_url}/api/v1/cache/{private_cache_name}?",
        headers=[f"Authorization: Bearer {private_cache_token}"],
    )
    assert status == 200
    assert payload["name"] == private_cache_name
    assert payload["isPublic"] is False


@pytest.mark.security
def test_private_nix_cache_requires_credentials(
    http_request: Callable[..., tuple[int, str]],
    private_nix_cache_url: str,
    private_cache_token: str,
) -> None:
    status, _ = http_request(f"{private_nix_cache_url}/nix-cache-info")
    assert status == 401

    status, _ = http_request(
        f"{private_nix_cache_url}/nix-cache-info",
        headers=[_basic_auth("invalid-token")],
    )
    assert status == 401

    status, body = http_request(
        f"{private_nix_cache_url}/nix-cache-info",
        headers=[_basic_auth(private_cache_token)],
    )
    assert status == 200
    assert "StoreDir: /nix/store" in body


@pytest.mark.security
def test_cache_write_without_authorization_header_returns_401(
    require_api_endpoint: None,
    http_request: Callable[..., tuple[int, str]],
    api_base_url: str,
    cache_name: str,
) -> None:
    del require_api_endpoint
    status, _ = http_request(
        url=f"{api_base_url}/api/v1/cache/{cache_name}/narinfo",
        method="POST",
        headers=["Content-Type: application/json"],
        data=json.dumps([]),
    )
    assert status == 401


@pytest.mark.security
def test_cache_token_cannot_be_forged_from_name(
    require_api_endpoint: None,
    http_request: Callable[..., tuple[int, str]],
    api_base_url: str,
    cache_name: str,
    server_key: str,
) -> None:
    del require_api_endpoint
    for key in sorted({"", server_key}):
        forged = _forge_hs256({"name": cache_name}, key)
        status, _ = http_request(
            url=f"{api_base_url}/api/v1/cache/{cache_name}/narinfo",
            method="POST",
            headers=[f"Authorization: Bearer {forged}", "Content-Type: application/json"],
            data=json.dumps([]),
        )
        assert status == 401, f"token forged with key {key!r} was accepted"


@pytest.mark.security
def test_workspace_token_cannot_write_to_cache(
    require_api_endpoint: None,
    http_request: Callable[..., tuple[int, str]],
    api_base_url: str,
    cache_name: str,
    workspace_token: str,
) -> None:
    """The test server has a workspace named like the cache; its token must not grant cache access."""
    del require_api_endpoint
    status, _ = http_request(
        url=f"{api_base_url}/api/v1/cache/{cache_name}/narinfo",
        method="POST",
        headers=[f"Authorization: Bearer {workspace_token}", "Content-Type: application/json"],
        data=json.dumps([]),
    )
    assert status == 401
