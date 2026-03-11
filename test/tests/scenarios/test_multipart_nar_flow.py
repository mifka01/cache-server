from __future__ import annotations

import json
import uuid
from typing import Any, Callable

import pytest


@pytest.mark.scenario
@pytest.mark.requires_token
def test_multipart_nar_abort_rejects_followup_put(
    require_api_endpoint: None,
    require_cache_token: None,
    request_json: Callable[..., tuple[int, Any]],
    http_request: Callable[..., tuple[int, str]],
    api_base_url: str,
    cache_name: str,
    nix_cache_url: str,
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

    nar_id = str(payload["narId"])

    abort_status, _ = http_request(
        url=f"{api_base_url}/api/v1/cache/{cache_name}/multipart-nar/{nar_id}/abort",
        method="POST",
        headers=[f"Authorization: Bearer {cache_auth_token}"],
        data="{}",
    )
    assert abort_status == 200

    put_status, _ = http_request(
        url=f"{nix_cache_url}/{nar_id}",
        method="PUT",
        data="chunk-after-abort",
    )
    assert put_status == 400


@pytest.mark.scenario
@pytest.mark.requires_token
def test_multipart_nar_complete_creates_retrievable_narinfo(
    require_api_endpoint: None,
    require_cache_token: None,
    request_json: Callable[..., tuple[int, Any]],
    http_request: Callable[..., tuple[int, str]],
    api_base_url: str,
    cache_name: str,
    nix_cache_url: str,
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

    nar_id = str(payload["narId"])
    put_status, _ = http_request(
        url=f"{nix_cache_url}/{nar_id}",
        method="PUT",
        data="multipart-content",
    )
    assert put_status == 201

    store_hash = f"qa{uuid.uuid4().hex[:10]}"
    file_hash = f"qa{uuid.uuid4().hex[:10]}"
    complete_body = {
        "narInfoCreate": {
            "cStoreHash": store_hash,
            "cStoreSuffix": "qa-multipart",
            "cFileHash": file_hash,
            "cFileSize": 17,
            "cNarHash": "sha256:qa",
            "cNarSize": 17,
            "cDeriver": "unknown",
            "cReferences": [],
        }
    }

    complete_status, _ = http_request(
        url=f"{api_base_url}/api/v1/cache/{cache_name}/multipart-nar/{nar_id}/complete",
        method="POST",
        headers=[
            f"Authorization: Bearer {cache_auth_token}",
            "Content-Type: application/json",
        ],
        data=json.dumps(complete_body),
    )
    assert complete_status == 200

    narinfo_status, narinfo = http_request(f"{nix_cache_url}/{store_hash}.narinfo")
    assert narinfo_status == 200
    assert "StorePath:" in narinfo
