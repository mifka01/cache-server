from __future__ import annotations

from typing import Any, Callable

import pytest

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
    upload_parts: Callable[[list[bytes]], tuple[str, list[dict[str, Any]]]],
    complete_upload: Callable[..., int],
    abort_upload: Callable[[str], int],
    narinfo_create: Callable[..., dict[str, Any]],
    http_request: Callable[..., tuple[int, str]],
    nix_cache_url: str,
) -> None:
    del require_api_endpoint, require_cache_token
    nar_id, parts = upload_parts([b"data"])
    narinfo = narinfo_create(b"data")
    store_hash = narinfo["cStoreHash"]
    narinfo.update(overrides)

    assert complete_upload(nar_id, narinfo, parts) == 400

    if "cStoreHash" not in overrides:
        narinfo_status, _ = http_request(f"{nix_cache_url}/{store_hash}.narinfo")
        assert narinfo_status == 404

    assert abort_upload(nar_id) == 200


@pytest.mark.security
@pytest.mark.requires_token
def test_upload_complete_accepts_dot_leading_store_names(
    require_api_endpoint: None,
    require_cache_token: None,
    upload_parts: Callable[[list[bytes]], tuple[str, list[dict[str, Any]]]],
    complete_upload: Callable[..., int],
    narinfo_create: Callable[..., dict[str, Any]],
    random_nix_hash: Callable[[int], str],
    http_request: Callable[..., tuple[int, str]],
    nix_cache_url: str,
) -> None:
    """Nix allows names like `.zshrc` (from `${./.zshrc}`); validation must not break pushing them."""
    del require_api_endpoint, require_cache_token
    nar_id, parts = upload_parts([b"data"])
    reference = f"{random_nix_hash(32)}-.qa-dotfile-dep"
    narinfo = narinfo_create(
        b"data",
        cStoreSuffix=".qa-dotfile",
        cDeriver=f"{random_nix_hash(32)}-.qa-dotfile.drv",
        cReferences=[reference],
    )

    assert complete_upload(nar_id, narinfo, parts) == 200

    narinfo_status, text = http_request(f"{nix_cache_url}/{narinfo['cStoreHash']}.narinfo")
    assert narinfo_status == 200
    assert f"StorePath: /nix/store/{narinfo['cStoreHash']}-.qa-dotfile" in text
    assert reference in text


@pytest.mark.security
@pytest.mark.requires_token
def test_upload_id_is_not_published_to_dht(
    require_api_endpoint: None,
    require_cache_token: None,
    upload_parts: Callable[[list[bytes]], tuple[str, list[dict[str, Any]]]],
    dht_values: Callable[[str], list[str]],
) -> None:
    """The upload URL is the only credential for PUT, so its id must stay secret."""
    del require_api_endpoint, require_cache_token
    nar_id, _ = upload_parts([b"data"])

    for key in (nar_id, f"{nar_id}.nar.xz"):
        assert dht_values(key) == []
