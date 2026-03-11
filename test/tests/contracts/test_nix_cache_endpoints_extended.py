from __future__ import annotations

from typing import Callable

import pytest


@pytest.mark.contract
def test_missing_narinfo_returns_404(
    require_nix_cache_endpoint: None,
    http_request: Callable[..., tuple[int, str]],
    nix_cache_url: str,
) -> None:
    del require_nix_cache_endpoint
    status, _ = http_request(f"{nix_cache_url}/deadbeef.narinfo")
    assert status == 404


@pytest.mark.contract
def test_missing_nar_blob_returns_404(
    require_nix_cache_endpoint: None,
    http_request: Callable[..., tuple[int, str]],
    nix_cache_url: str,
) -> None:
    del require_nix_cache_endpoint
    status, _ = http_request(f"{nix_cache_url}/nar/deadbeef.nar.xz")
    assert status == 404


@pytest.mark.contract
@pytest.mark.requires_cachix
@pytest.mark.requires_token
def test_narinfo_head_for_existing_path_returns_200(
    require_nix_cache_endpoint: None,
    require_cache_token: None,
    create_sample_store_path: Callable[[str], str],
    push_store_path: Callable[[str], object],
    extract_store_hash: Callable[[str], str],
    http_request: Callable[..., tuple[int, str]],
    nix_cache_url: str,
) -> None:
    del require_nix_cache_endpoint, require_cache_token
    store_path = create_sample_store_path("qa-head")
    push_store_path(store_path)

    store_hash = extract_store_hash(store_path)
    status, _ = http_request(f"{nix_cache_url}/{store_hash}.narinfo", method="HEAD")
    assert status == 200


@pytest.mark.contract
@pytest.mark.requires_cachix
@pytest.mark.requires_token
def test_narinfo_has_required_fields_after_push(
    require_nix_cache_endpoint: None,
    require_cache_token: None,
    create_sample_store_path: Callable[[str], str],
    push_store_path: Callable[[str], object],
    extract_store_hash: Callable[[str], str],
    http_request: Callable[..., tuple[int, str]],
    nix_cache_url: str,
) -> None:
    del require_nix_cache_endpoint, require_cache_token
    store_path = create_sample_store_path("qa-fields")
    push_store_path(store_path)

    store_hash = extract_store_hash(store_path)
    status, narinfo = http_request(f"{nix_cache_url}/{store_hash}.narinfo")
    assert status == 200
    assert "StorePath:" in narinfo
    assert "NarHash:" in narinfo
    assert "URL:" in narinfo
    assert "Compression:" in narinfo
