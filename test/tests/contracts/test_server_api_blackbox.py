from __future__ import annotations

import json
from typing import Any, Callable

import pytest


@pytest.mark.contract
def test_dht_put_and_get_endpoint_contract(
    require_api_endpoint: None,
    request_json: Callable[..., tuple[int, Any]],
    api_base_url: str,
) -> None:
    del require_api_endpoint

    key = "qa-dht-contract-key"
    value = "ok"
    put_status, _ = request_json(
        url=f"{api_base_url}/api/v1/dht/put",
        method="POST",
        headers=["Content-Type: application/json"],
        data=json.dumps({"key": key, "value": value, "permanent": False}),
    )
    assert put_status == 200

    get_status, payload = request_json(url=f"{api_base_url}/api/v1/dht/get/{key}")
    assert get_status == 200
    assert isinstance(payload, dict)
    assert "value" in payload
