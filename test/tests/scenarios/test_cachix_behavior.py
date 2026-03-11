from __future__ import annotations

import os
import shutil
import subprocess
from typing import Callable

import pytest


@pytest.mark.scenario
@pytest.mark.requires_cachix
def test_cachix_use_is_idempotent(
    require_api_endpoint: None,
    run_cmd: Callable[[list[str]], subprocess.CompletedProcess[str]],
    cache_name: str,
) -> None:
    del require_api_endpoint
    if shutil.which("cachix") is None:
        pytest.skip("cachix is not available in PATH")

    run_cmd(["cachix", "use", cache_name])
    run_cmd(["cachix", "use", cache_name])


@pytest.mark.scenario
@pytest.mark.requires_cachix
@pytest.mark.requires_token
def test_cachix_push_same_path_twice_is_safe(
    require_cache_token: None,
    create_sample_store_path: Callable[[str], str],
    push_store_path: Callable[[str], object],
) -> None:
    del require_cache_token
    if shutil.which("cachix") is None:
        pytest.skip("cachix is not available in PATH")

    store_path = create_sample_store_path("qa-same")
    push_store_path(store_path)
    push_store_path(store_path)


@pytest.mark.scenario
@pytest.mark.requires_cachix
@pytest.mark.requires_token
def test_cachix_push_with_invalid_token_fails(
    cache_name: str,
    create_sample_store_path: Callable[[str], str],
) -> None:
    if shutil.which("cachix") is None:
        pytest.skip("cachix is not available in PATH")

    store_path = create_sample_store_path("qa-invalid-token")
    env = dict(os.environ)
    env["CACHIX_AUTH_TOKEN"] = "invalid-token"

    result = subprocess.run(
        ["cachix", "push", cache_name],
        input=f"{store_path}\n",
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert result.returncode != 0


@pytest.mark.scenario
@pytest.mark.requires_cachix
def test_cachix_config_points_to_server_vm(
    run_cmd: Callable[[list[str]], subprocess.CompletedProcess[str]],
) -> None:
    if shutil.which("cachix") is None:
        pytest.skip("cachix is not available in PATH")

    hostname = run_cmd(["cachix", "config", "get", "hostname"]).stdout.strip()
    assert "http://servera:5001" in hostname


@pytest.mark.scenario
@pytest.mark.requires_cachix
@pytest.mark.requires_token
def test_cachix_push_multiple_paths(
    require_cache_token: None,
    cache_name: str,
    create_sample_store_path: Callable[[str], str],
    extract_store_hash: Callable[[str], str],
    http_request: Callable[..., tuple[int, str]],
    nix_cache_url: str,
) -> None:
    del require_cache_token
    if shutil.which("cachix") is None:
        pytest.skip("cachix is not available in PATH")

    path_a = create_sample_store_path("qa-multi-a")
    path_b = create_sample_store_path("qa-multi-b")

    result = subprocess.run(
        ["cachix", "push", cache_name],
        input=f"{path_a}\n{path_b}\n",
        text=True,
        capture_output=True,
        check=True,
    )
    assert result.returncode == 0

    hash_a = extract_store_hash(path_a)
    hash_b = extract_store_hash(path_b)
    status_a, _ = http_request(f"{nix_cache_url}/{hash_a}.narinfo")
    status_b, _ = http_request(f"{nix_cache_url}/{hash_b}.narinfo")
    assert status_a == 200
    assert status_b == 200
