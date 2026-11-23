from __future__ import annotations

import base64
import hashlib
from typing import Any, Callable

import pytest


@pytest.mark.scenario
@pytest.mark.requires_token
def test_multipart_nar_abort_rejects_followup_put(
    require_api_endpoint: None,
    require_cache_token: None,
    create_upload: Callable[[], str],
    part_url: Callable[[str, int, bytes], str],
    put_part: Callable[..., tuple[int, dict[str, str]]],
    abort_upload: Callable[[str], int],
) -> None:
    del require_api_endpoint, require_cache_token
    nar_id = create_upload()
    url = part_url(nar_id, 1, b"chunk-after-abort")

    assert abort_upload(nar_id) == 200

    put_status, _ = put_part(url, b"chunk-after-abort")
    assert put_status == 400


@pytest.mark.scenario
@pytest.mark.requires_token
def test_multipart_nar_parts_are_assembled_in_order(
    require_api_endpoint: None,
    require_cache_token: None,
    upload_parts: Callable[[list[bytes]], tuple[str, list[dict[str, Any]]]],
    complete_upload: Callable[..., int],
    narinfo_create: Callable[..., dict[str, Any]],
    narinfo_value: Callable[[str, str], str],
    http_request: Callable[..., tuple[int, str]],
    nix_cache_url: str,
) -> None:
    del require_api_endpoint, require_cache_token
    parts = [b"first-part|", b"second-part|", b"third-part"]
    data = b"".join(parts)

    nar_id, completed = upload_parts(parts)
    narinfo = narinfo_create(data, cStoreSuffix="qa-multipart")
    assert complete_upload(nar_id, narinfo, completed) == 200

    narinfo_status, text = http_request(f"{nix_cache_url}/{narinfo['cStoreHash']}.narinfo")
    assert narinfo_status == 200
    assert narinfo_value(text, "StorePath") == f"/nix/store/{narinfo['cStoreHash']}-qa-multipart"
    assert narinfo_value(text, "FileSize") == str(len(data))

    nar_status, nar = http_request(f"{nix_cache_url}/{narinfo_value(text, 'URL')}")
    assert nar_status == 200
    assert nar == data.decode()


@pytest.mark.scenario
@pytest.mark.requires_token
def test_multipart_complete_rejects_content_not_matching_file_hash(
    require_api_endpoint: None,
    require_cache_token: None,
    upload_parts: Callable[[list[bytes]], tuple[str, list[dict[str, Any]]]],
    complete_upload: Callable[..., int],
    narinfo_create: Callable[..., dict[str, Any]],
    http_request: Callable[..., tuple[int, str]],
    nix_cache_url: str,
) -> None:
    del require_api_endpoint, require_cache_token
    nar_id, completed = upload_parts([b"uploaded-content"])
    narinfo = narinfo_create(b"claimed-content!")

    assert complete_upload(nar_id, narinfo, completed) == 400

    narinfo_status, _ = http_request(f"{nix_cache_url}/{narinfo['cStoreHash']}.narinfo")
    assert narinfo_status == 404


@pytest.mark.scenario
@pytest.mark.requires_token
def test_multipart_complete_rejects_part_that_was_not_uploaded(
    require_api_endpoint: None,
    require_cache_token: None,
    upload_parts: Callable[[list[bytes]], tuple[str, list[dict[str, Any]]]],
    complete_upload: Callable[..., int],
    narinfo_create: Callable[..., dict[str, Any]],
) -> None:
    del require_api_endpoint, require_cache_token
    nar_id, completed = upload_parts([b"only-part"])
    missing = {"partNumber": 2, "eTag": completed[0]["eTag"]}

    assert complete_upload(nar_id, narinfo_create(b"only-part"), [*completed, missing]) == 400


@pytest.mark.scenario
@pytest.mark.requires_token
def test_multipart_part_rejects_wrong_content_md5(
    require_api_endpoint: None,
    require_cache_token: None,
    create_upload: Callable[[], str],
    part_url: Callable[[str, int, bytes], str],
    put_part: Callable[..., tuple[int, dict[str, str]]],
) -> None:
    del require_api_endpoint, require_cache_token
    nar_id = create_upload()
    url = part_url(nar_id, 1, b"expected")

    expected_md5 = base64.b64encode(hashlib.md5(b"expected").digest()).decode()
    status, _ = put_part(url, b"corrupted", content_md5=expected_md5)
    assert status == 400


@pytest.mark.scenario
@pytest.mark.requires_token
def test_multipart_failed_retry_keeps_accepted_part(
    require_api_endpoint: None,
    require_cache_token: None,
    upload_parts: Callable[[list[bytes]], tuple[str, list[dict[str, Any]]]],
    part_url: Callable[[str, int, bytes], str],
    put_part: Callable[..., tuple[int, dict[str, str]]],
    complete_upload: Callable[..., int],
    narinfo_create: Callable[..., dict[str, Any]],
    http_request: Callable[..., tuple[int, str]],
    nix_cache_url: str,
) -> None:
    """cachix retries parts; a retry that fails verification must not replace the part already stored."""
    del require_api_endpoint, require_cache_token
    nar_id, completed = upload_parts([b"accepted-part"])

    accepted_md5 = base64.b64encode(hashlib.md5(b"accepted-part").digest()).decode()
    status, _ = put_part(part_url(nar_id, 1, b"accepted-part"), b"corrupted-retry", content_md5=accepted_md5)
    assert status == 400

    narinfo = narinfo_create(b"accepted-part")
    assert complete_upload(nar_id, narinfo, completed) == 200
    narinfo_status, _ = http_request(f"{nix_cache_url}/{narinfo['cStoreHash']}.narinfo")
    assert narinfo_status == 200
