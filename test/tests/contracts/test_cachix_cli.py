from __future__ import annotations

import shutil
import subprocess
from typing import Callable

import pytest


@pytest.mark.contract
@pytest.mark.requires_cachix
def test_cachix_cli_can_use_cache(
    require_api_endpoint: None,
    run_cmd: Callable[[list[str]], subprocess.CompletedProcess[str]],
    cache_name: str,
) -> None:
    del require_api_endpoint
    if shutil.which("cachix") is None:
        pytest.skip("cachix is not available in PATH")

    try:
        run_cmd(["cachix", "use", cache_name])
    except subprocess.CalledProcessError as exc:
        combined = f"{exc.stdout}\n{exc.stderr}"
        if "doesn't have permissions to configure binary caches" in combined:
            pytest.skip("Host Nix permissions do not allow cachix use mutation")
        raise
