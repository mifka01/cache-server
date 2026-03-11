from __future__ import annotations

import json
from typing import Any, Callable

import pytest


@pytest.mark.contract
def test_unknown_cache_returns_400(
    require_api_endpoint: None,
    http_request: Callable[..., tuple[int, str]],
    api_base_url: str,
) -> None:
    del require_api_endpoint
    status, _ = http_request(f"{api_base_url}/api/v1/cache/doesnotexist?")
    assert status == 400


@pytest.mark.contract
@pytest.mark.requires_token
def test_narinfo_missing_hashes_endpoint_shape(
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


@pytest.mark.contract
@pytest.mark.requires_token
def test_multipart_nar_create_endpoint_contract(
    require_api_endpoint: None,
    require_cache_token: None,
    request_json: Callable[..., tuple[int, Any]],
    api_base_url: str,
    cache_name: str,
    cache_auth_token: str,
) -> None:
    del require_api_endpoint, require_cache_token
    status, payload = request_json(
        url=f"{api_base_url}/api/v1/cache/{cache_name}/multipart-nar?compression=xz",
        method="POST",
        headers=[f"Authorization: Bearer {cache_auth_token}"],
        data="{}",
    )
    assert status == 200
    assert isinstance(payload, dict)
    assert "narId" in payload
    assert "uploadId" in payload
    assert len(str(payload["narId"])) > 10
    assert len(str(payload["uploadId"])) > 10
