from __future__ import annotations

from typing import Callable

import pytest


@pytest.mark.security
@pytest.mark.requires_token
def test_oversized_request_body_is_rejected_before_reading(
    require_api_endpoint: None,
    require_cache_token: None,
    http_request: Callable[..., tuple[int, str]],
    api_base_url: str,
    cache_name: str,
    cache_auth_token: str,
) -> None:
    """A huge Content-Length must not make the server buffer (or wait for) the whole body."""
    del require_api_endpoint, require_cache_token
    status, _ = http_request(
        url=f"{api_base_url}/api/v1/cache/{cache_name}/narinfo",
        method="POST",
        headers=[
            f"Authorization: Bearer {cache_auth_token}",
            "Content-Type: application/json",
            "Content-Length: 1073741824",
        ],
        data="[]",
    )
    assert status == 413


@pytest.mark.security
@pytest.mark.requires_token
def test_request_body_without_content_length_is_rejected(
    require_api_endpoint: None,
    require_cache_token: None,
    http_request: Callable[..., tuple[int, str]],
    api_base_url: str,
    cache_name: str,
    cache_auth_token: str,
) -> None:
    del require_api_endpoint, require_cache_token
    status, _ = http_request(
        url=f"{api_base_url}/api/v1/cache/{cache_name}/narinfo",
        method="POST",
        headers=[f"Authorization: Bearer {cache_auth_token}"],
    )
    assert status == 411
