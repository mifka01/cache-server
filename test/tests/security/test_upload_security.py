from __future__ import annotations

import json
from typing import Any, Callable

import pytest


def _narinfo_create(store_hash: str, file_hash: str, **overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "cStoreHash": store_hash,
        "cStoreSuffix": "qa-upload-security",
        "cFileHash": file_hash,
        "cFileSize": 4,
        "cNarHash": f"sha256:{file_hash}",
        "cNarSize": 4,
        "cDeriver": "unknown-deriver",
        "cReferences": [],
    }
    body.update(overrides)
    return {"narInfoCreate": body}


INVALID_FIELDS = {
    "file-hash-traversal": {"cFileHash": "../../../../../../tmp/qa-escape"},
    "file-hash-absolute": {"cFileHash": "/tmp/qa-escape"},
    "file-hash-not-a-hash": {"cFileHash": "key"},
    "store-hash-traversal": {"cStoreHash": "../qa-escape"},
    "store-hash-newline": {"cStoreHash": "qa\nURL: nar/evil.nar.xz"},
    "suffix-newline-injection": {"cStoreSuffix": "qa\nURL: nar/evil.nar.xz"},
    "deriver-newline-injection": {"cDeriver": "x.drv\nURL: nar/evil.nar.xz"},
    "deriver-not-a-derivation": {"cDeriver": "foo"},
    "deriver-missing": {"cDeriver": None},
    "nar-hash-newline-injection": {"cNarHash": "sha256:abc\nURL: nar/evil.nar.xz"},
    "reference-newline-injection": {"cReferences": ["qa\nURL: nar/evil.nar.xz"]},
    "negative-size": {"cFileSize": -1},
}


@pytest.mark.security
@pytest.mark.requires_token
@pytest.mark.parametrize("overrides", INVALID_FIELDS.values(), ids=INVALID_FIELDS.keys())
def test_upload_complete_rejects_invalid_narinfo_fields(
    overrides: dict[str, Any],
    require_api_endpoint: None,
    require_cache_token: None,
    create_upload: Callable[[], str],
    http_request: Callable[..., tuple[int, str]],
    random_nix_hash: Callable[[int], str],
    api_base_url: str,
    nix_cache_url: str,
    cache_name: str,
    cache_auth_token: str,
) -> None:
    del require_api_endpoint, require_cache_token
    nar_id = create_upload()
    put_status, _ = http_request(url=f"{nix_cache_url}/{nar_id}", method="PUT", data="data")
    assert put_status == 201

    store_hash = random_nix_hash(32)
    body = _narinfo_create(store_hash, random_nix_hash(52), **overrides)
    upload_url = f"{api_base_url}/api/v1/cache/{cache_name}/multipart-nar/{nar_id}"
    auth = f"Authorization: Bearer {cache_auth_token}"

    status, _ = http_request(
        url=f"{upload_url}/complete",
        method="POST",
        headers=[auth, "Content-Type: application/json"],
        data=json.dumps(body),
    )
    assert status == 400

    if "cStoreHash" not in overrides:
        narinfo_status, _ = http_request(f"{nix_cache_url}/{store_hash}.narinfo")
        assert narinfo_status == 404

    abort_status, _ = http_request(url=f"{upload_url}/abort", method="POST", headers=[auth], data="{}")
    assert abort_status == 200


@pytest.mark.security
@pytest.mark.requires_token
def test_upload_complete_accepts_dot_leading_store_names(
    require_api_endpoint: None,
    require_cache_token: None,
    create_upload: Callable[[], str],
    http_request: Callable[..., tuple[int, str]],
    random_nix_hash: Callable[[int], str],
    api_base_url: str,
    nix_cache_url: str,
    cache_name: str,
    cache_auth_token: str,
) -> None:
    """Nix allows names like `.zshrc` (from `${./.zshrc}`); validation must not break pushing them."""
    del require_api_endpoint, require_cache_token
    nar_id = create_upload()
    put_status, _ = http_request(url=f"{nix_cache_url}/{nar_id}", method="PUT", data="data")
    assert put_status == 201

    store_hash = random_nix_hash(32)
    reference = f"{random_nix_hash(32)}-.qa-dotfile-dep"
    body = _narinfo_create(
        store_hash,
        random_nix_hash(52),
        cStoreSuffix=".qa-dotfile",
        cDeriver=f"{random_nix_hash(32)}-.qa-dotfile.drv",
        cReferences=[reference],
    )
    status, _ = http_request(
        url=f"{api_base_url}/api/v1/cache/{cache_name}/multipart-nar/{nar_id}/complete",
        method="POST",
        headers=[f"Authorization: Bearer {cache_auth_token}", "Content-Type: application/json"],
        data=json.dumps(body),
    )
    assert status == 200

    narinfo_status, narinfo = http_request(f"{nix_cache_url}/{store_hash}.narinfo")
    assert narinfo_status == 200
    assert f"StorePath: /nix/store/{store_hash}-.qa-dotfile" in narinfo
    assert reference in narinfo


@pytest.mark.security
@pytest.mark.requires_token
def test_upload_id_is_not_published_to_dht(
    require_api_endpoint: None,
    require_cache_token: None,
    create_upload: Callable[[], str],
    http_request: Callable[..., tuple[int, str]],
    dht_values: Callable[[str], list[str]],
    nix_cache_url: str,
) -> None:
    """The upload URL is the only credential for PUT, so its id must stay secret."""
    del require_api_endpoint, require_cache_token
    nar_id = create_upload()
    put_status, _ = http_request(url=f"{nix_cache_url}/{nar_id}", method="PUT", data="data")
    assert put_status == 201

    for key in (nar_id, f"{nar_id}.nar.xz"):
        assert dht_values(key) == []
