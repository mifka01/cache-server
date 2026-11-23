from __future__ import annotations

import shutil
import subprocess
from typing import Callable

import pytest

# cachix uploads NARs in 32 MiB parts, four at a time.
CACHIX_PART_SIZE = 32 * 1024 * 1024


@pytest.mark.scenario
@pytest.mark.requires_cachix
@pytest.mark.requires_token
def test_push_larger_than_one_upload_part_can_be_substituted(
    require_nix_cache_endpoint: None,
    require_cache_token: None,
    run_cmd: Callable[[list[str]], subprocess.CompletedProcess[str]],
    push_store_path: Callable[[str], object],
    extract_store_hash: Callable[[str], str],
    http_request: Callable[..., tuple[int, str]],
    narinfo_value: Callable[[str, str], str],
    nix_cache_url: str,
) -> None:
    del require_nix_cache_endpoint, require_cache_token
    if shutil.which("cachix") is None:
        pytest.skip("cachix is not available in PATH")

    # Random content does not compress, so the uploaded NAR spans several parts.
    store_path = run_cmd(
        [
            "sh",
            "-c",
            "head -c 100M /dev/urandom > /tmp/qa-large.bin && nix-store --add /tmp/qa-large.bin && rm /tmp/qa-large.bin",
        ]
    ).stdout.strip()
    push_store_path(store_path)

    status, narinfo = http_request(f"{nix_cache_url}/{extract_store_hash(store_path)}.narinfo")
    assert status == 200
    assert int(narinfo_value(narinfo, "FileSize")) > 2 * CACHIX_PART_SIZE

    # Nix checks the NAR hash on import, so a reassembled NAR must be byte-identical.
    run_cmd(["nix-store", "--delete", store_path])
    run_cmd(
        [
            "nix",
            "--extra-experimental-features",
            "nix-command",
            "copy",
            "--from",
            nix_cache_url,
            "--no-check-sigs",
            store_path,
        ]
    )
    run_cmd(["nix-store", "--verify-path", store_path])
