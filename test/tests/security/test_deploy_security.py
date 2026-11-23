from __future__ import annotations

import json
import uuid
from typing import Any, Callable

import pytest


@pytest.mark.security
def test_deploy_activate_requires_workspace_token(
    require_api_endpoint: None,
    http_request: Callable[..., tuple[int, str]],
    api_base_url: str,
) -> None:
    del require_api_endpoint
    body = json.dumps({"agents": {}})

    status, _ = http_request(
        url=f"{api_base_url}/api/v2/deploy/activate",
        method="POST",
        headers=["Content-Type: application/json"],
        data=body,
    )
    assert status == 401

    status, _ = http_request(
        url=f"{api_base_url}/api/v2/deploy/activate",
        method="POST",
        headers=["Authorization: Bearer invalid-token", "Content-Type: application/json"],
        data=body,
    )
    assert status == 401


@pytest.mark.security
@pytest.mark.requires_token
def test_deploy_activate_rejects_cache_token(
    require_api_endpoint: None,
    require_cache_token: None,
    http_request: Callable[..., tuple[int, str]],
    api_base_url: str,
    cache_auth_token: str,
) -> None:
    del require_api_endpoint, require_cache_token
    status, _ = http_request(
        url=f"{api_base_url}/api/v2/deploy/activate",
        method="POST",
        headers=[f"Authorization: Bearer {cache_auth_token}", "Content-Type: application/json"],
        data=json.dumps({"agents": {}}),
    )
    assert status == 401


@pytest.mark.security
def test_deploy_activate_accepts_workspace_token(
    require_api_endpoint: None,
    request_json: Callable[..., tuple[int, Any]],
    api_base_url: str,
    workspace_token: str,
) -> None:
    del require_api_endpoint
    auth = f"Authorization: Bearer {workspace_token}"

    status, payload = request_json(
        url=f"{api_base_url}/api/v2/deploy/activate",
        method="POST",
        headers=[auth, "Content-Type: application/json"],
        data=json.dumps({"agents": {}}),
    )
    assert status == 200
    assert payload == {"agents": {}}

    status, _ = request_json(
        url=f"{api_base_url}/api/v2/deploy/activate",
        method="POST",
        headers=[auth, "Content-Type: application/json"],
        data=json.dumps({"agents": {"qa-unknown-agent": "/nix/store/x"}}),
    )
    assert status == 400


@pytest.mark.security
def test_deployment_status_requires_workspace_token(
    require_api_endpoint: None,
    http_request: Callable[..., tuple[int, str]],
    api_base_url: str,
    workspace_token: str,
) -> None:
    del require_api_endpoint
    url = f"{api_base_url}/api/v1/deploy/deployment/{uuid.uuid4()}"

    status, _ = http_request(url)
    assert status == 401

    status, _ = http_request(url, headers=[f"Authorization: Bearer {workspace_token}"])
    assert status == 404
