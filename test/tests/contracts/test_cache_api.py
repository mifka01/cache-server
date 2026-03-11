from __future__ import annotations

from typing import Callable

import pytest


@pytest.mark.contract
@pytest.mark.smoke
def test_cache_metadata_contract(
    require_api_endpoint: None,
    get_json: Callable[[str], dict],
    api_base_url: str,
    cache_name: str,
) -> None:
    del require_api_endpoint
    payload = get_json(f"{api_base_url}/api/v1/cache/{cache_name}?")
    assert payload["name"] == cache_name
    assert isinstance(payload["isPublic"], bool)
    assert isinstance(payload["publicSigningKeys"], list)
