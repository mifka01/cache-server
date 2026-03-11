from __future__ import annotations

import json
from typing import Any, Callable

import pytest


@pytest.mark.scenario
@pytest.mark.requires_token
def test_cache_write_endpoint_rejects_invalid_token(
    require_api_endpoint: None,
    require_cache_token: None,
    request_json: Callable[..., tuple[int, Any]],
    api_base_url: str,
    cache_name: str,
) -> None:
    del require_api_endpoint, require_cache_token

    status, _ = request_json(
        url=f"{api_base_url}/api/v1/cache/{cache_name}/narinfo",
        method="POST",
        headers=[
            "Authorization: Bearer invalid-token",
            "Content-Type: application/json",
        ],
        data=json.dumps([]),
    )
    assert status == 401


@pytest.mark.scenario
@pytest.mark.requires_token
def test_cache_write_endpoint_accepts_valid_token(
    require_api_endpoint: None,
    require_cache_token: None,
    request_json: Callable[..., tuple[int, Any]],
    api_base_url: str,
    cache_name: str,
    cache_auth_token: str,
) -> None:
    del require_api_endpoint, require_cache_token

    status, payload = request_json(
        url=f"{api_base_url}/api/v1/cache/{cache_name}/narinfo",
        method="POST",
        headers=[
            f"Authorization: Bearer {cache_auth_token}",
            "Content-Type: application/json",
        ],
        data=json.dumps([]),
    )
    assert status == 200
    assert isinstance(payload, list)
