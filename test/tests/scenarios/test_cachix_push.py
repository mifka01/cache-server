from __future__ import annotations

import os
import shutil
import subprocess
from typing import Callable

import pytest


@pytest.mark.scenario
@pytest.mark.requires_cachix
@pytest.mark.requires_token
def test_cachix_push_makes_narinfo_available(
    run_cmd: Callable[[list[str]], subprocess.CompletedProcess[str]],
    cache_name: str,
    nix_cache_url: str,
    create_sample_store_path: Callable[[str], str],
) -> None:
    if shutil.which("cachix") is None:
        pytest.skip("cachix is not available in PATH")

    if not os.environ.get("CACHIX_AUTH_TOKEN"):
        pytest.skip("CACHIX_AUTH_TOKEN is required for push scenario")

    store_path = create_sample_store_path("qa-basic-push")

    push = subprocess.run(
        ["sh", "-c", f"echo '{store_path}' | cachix push {cache_name}"],
        text=True,
        capture_output=True,
        check=True,
    )
    assert push.returncode == 0

    store_hash = store_path.split("/")[-1].split("-")[0]
    narinfo = run_cmd(["curl", "-fsS", f"{nix_cache_url}/{store_hash}.narinfo"]).stdout
    assert "StorePath:" in narinfo
