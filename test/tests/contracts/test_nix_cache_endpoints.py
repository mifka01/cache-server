from __future__ import annotations

from typing import Callable

import pytest


@pytest.mark.contract
@pytest.mark.smoke
def test_nix_cache_info_contract(
    require_nix_cache_endpoint: None,
    get_text: Callable[[str], str],
    nix_cache_url: str,
) -> None:
    del require_nix_cache_endpoint
    payload = get_text(f"{nix_cache_url}/nix-cache-info")
    assert "StoreDir: /nix/store" in payload
    assert "WantMassQuery: 1" in payload
