from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Callable

import pytest


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default).rstrip("/")


@pytest.fixture(scope="session")
def api_base_url() -> str:
    return _env("QA_API_BASE_URL", "http://127.0.0.1:5001")


@pytest.fixture(scope="session")
def nix_cache_url() -> str:
    return _env("QA_NIX_CACHE_URL", "http://127.0.0.1:7001")


@pytest.fixture(scope="session")
def cache_name() -> str:
    return os.environ.get("QA_CACHE_NAME", "main")


@pytest.fixture(scope="session")
def sample_store_path() -> str:
    return os.environ.get("QA_SAMPLE_STORE_PATH", "")


@pytest.fixture(scope="session")
def run_cmd() -> Callable[[list[str]], subprocess.CompletedProcess[str]]:
    def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(args, check=True, text=True, capture_output=True)

    return _run


def _wait_for_url(url: str, attempts: int = 10, timeout_seconds: int = 3) -> bool:
    for _ in range(attempts):
        result = subprocess.run(
            ["curl", "-fsS", "--max-time", str(timeout_seconds), url],
            text=True,
            capture_output=True,
        )
        if result.returncode == 0:
            return True
    return False


@pytest.fixture(scope="session")
def require_api_endpoint(api_base_url: str, cache_name: str) -> None:
    strict = os.environ.get("QA_STRICT_API", "0") == "1"
    if not _wait_for_url(f"{api_base_url}/api/v1/cache/{cache_name}?", attempts=5, timeout_seconds=2):
        if strict:
            raise RuntimeError(f"API endpoint not reachable: {api_base_url}")
        pytest.skip(f"API endpoint is not reachable: {api_base_url}")


@pytest.fixture(scope="session")
def require_nix_cache_endpoint(nix_cache_url: str) -> None:
    strict = os.environ.get("QA_STRICT_NIX_CACHE", "0") == "1"
    if not _wait_for_url(f"{nix_cache_url}/nix-cache-info", attempts=5, timeout_seconds=2):
        if strict:
            raise RuntimeError(f"Nix cache endpoint not reachable: {nix_cache_url}")
        pytest.skip(f"Nix cache endpoint is not reachable: {nix_cache_url}")


@pytest.fixture(scope="session")
def get_text() -> Callable[[str], str]:
    def _get(url: str) -> str:
        return subprocess.run(
            ["curl", "-fsS", "--max-time", "15", url],
            check=True,
            text=True,
            capture_output=True,
        ).stdout

    return _get


@pytest.fixture(scope="session")
def get_json() -> Callable[[str], dict]:
    def _get(url: str) -> dict:
        payload = subprocess.run(
            ["curl", "-fsS", "--max-time", "15", url],
            check=True,
            text=True,
            capture_output=True,
        ).stdout
        return json.loads(payload)

    return _get


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def cache_auth_token() -> str:
    return os.environ.get("CACHIX_AUTH_TOKEN", "")


@pytest.fixture(scope="session")
def require_cache_token(cache_auth_token: str) -> None:
    if not cache_auth_token:
        pytest.skip("CACHIX_AUTH_TOKEN is required")


@pytest.fixture(scope="session")
def run_cmd_no_check() -> Callable[[list[str]], subprocess.CompletedProcess[str]]:
    def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(args, check=False, text=True, capture_output=True)

    return _run


@pytest.fixture(scope="session")
def create_sample_store_path(run_cmd: Callable[[list[str]], subprocess.CompletedProcess[str]]) -> Callable[[str], str]:
    def _create(content: str = "qa-sample") -> str:
        return run_cmd(
            [
                "sh",
                "-c",
                f"printf '%s' '{content}' > /tmp/qa-sample.txt && nix-store --add /tmp/qa-sample.txt",
            ]
        ).stdout.strip()

    return _create


@pytest.fixture(scope="session")
def push_store_path(
    cache_name: str,
) -> Callable[[str], subprocess.CompletedProcess[str]]:
    def _push(path: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["cachix", "push", cache_name],
            input=f"{path}\n",
            text=True,
            capture_output=True,
            check=True,
        )

    return _push


@pytest.fixture(scope="session")
def extract_store_hash() -> Callable[[str], str]:
    def _extract(path: str) -> str:
        return path.split("/")[-1].split("-")[0]

    return _extract


@pytest.fixture(scope="session")
def http_request() -> Callable[..., tuple[int, str]]:
    def _request(
        url: str,
        method: str = "GET",
        headers: list[str] | None = None,
        data: str | None = None,
    ) -> tuple[int, str]:
        args = ["curl", "-sS", "-X", method, "--max-time", "20", "-w", "\n%{http_code}"]
        if headers:
            for header in headers:
                args.extend(["-H", header])
        if data is not None:
            args.extend(["-d", data])
        args.append(url)

        result = subprocess.run(args, check=False, text=True, capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(f"curl failed: {result.stderr.strip()}")

        lines = result.stdout.splitlines()
        if not lines:
            raise RuntimeError("empty response from curl")

        status = int(lines[-1])
        body = "\n".join(lines[:-1])
        return status, body

    return _request


@pytest.fixture(scope="session")
def request_json(http_request: Callable[..., tuple[int, str]]) -> Callable[..., tuple[int, Any]]:
    def _request_json(
        url: str,
        method: str = "GET",
        headers: list[str] | None = None,
        data: str | None = None,
    ) -> tuple[int, Any]:
        status, body = http_request(url=url, method=method, headers=headers, data=data)
        if not body:
            return status, None
        return status, json.loads(body)

    return _request_json
