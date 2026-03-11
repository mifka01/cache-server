from __future__ import annotations

import os
import shutil
import subprocess
from typing import Callable

import pytest


def _narinfo_value(narinfo: str, key: str) -> str:
    prefix = f"{key}: "
    for line in narinfo.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :]
    raise AssertionError(f"Missing key in narinfo: {key}")


@pytest.mark.scenario
@pytest.mark.requires_cachix
@pytest.mark.requires_token
def test_pushed_path_nar_download_is_available(
    require_nix_cache_endpoint: None,
    require_cache_token: None,
    create_sample_store_path: Callable[[str], str],
    push_store_path: Callable[[str], object],
    extract_store_hash: Callable[[str], str],
    http_request: Callable[..., tuple[int, str]],
    run_cmd: Callable[[list[str]], subprocess.CompletedProcess[str]],
    nix_cache_url: str,
) -> None:
    del require_nix_cache_endpoint, require_cache_token
    if shutil.which("cachix") is None:
        pytest.skip("cachix is not available in PATH")

    store_path = create_sample_store_path("qa-download")
    push_store_path(store_path)
    store_hash = extract_store_hash(store_path)

    narinfo_status, narinfo = http_request(f"{nix_cache_url}/{store_hash}.narinfo")
    assert narinfo_status == 200

    nar_url = _narinfo_value(narinfo, "URL")
    target_file = "/tmp/qa-downloaded.nar"
    run_cmd(["sh", "-c", f"curl -fsS '{nix_cache_url}/{nar_url}' -o {target_file}"])

    assert os.path.exists(target_file)
    assert os.path.getsize(target_file) > 0
