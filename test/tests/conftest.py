from __future__ import annotations

import json
import os
import secrets
import subprocess
from pathlib import Path
from typing import Any, Callable

import pytest

NIX_BASE32_ALPHABET = "0123456789abcdfghijklmnpqrsvwxyz"


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default).rstrip("/")


def _required_env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        pytest.skip(f"{name} is required")
    return value.rstrip("/")


@pytest.fixture(scope="session")
def private_cache_name() -> str:
    return _required_env("QA_PRIVATE_CACHE_NAME")


@pytest.fixture(scope="session")
def private_nix_cache_url() -> str:
    return _required_env("QA_PRIVATE_NIX_CACHE_URL")


@pytest.fixture(scope="session")
def private_cache_token() -> str:
    return _required_env("QA_PRIVATE_CACHE_TOKEN")


@pytest.fixture(scope="session")
def cache_id() -> str:
    return _required_env("QA_CACHE_ID")


@pytest.fixture(scope="session")
def workspace_token() -> str:
    return _required_env("QA_WORKSPACE_TOKEN")


@pytest.fixture(scope="session")
def server_key() -> str:
    """Value of `server.key` in the server config; empty when unset."""
    return os.environ.get("QA_SERVER_KEY", "")


@pytest.fixture(scope="session")
def random_nix_hash() -> Callable[[int], str]:
    def _hash(length: int = 32) -> str:
        return "".join(secrets.choice(NIX_BASE32_ALPHABET) for _ in range(length))

    return _hash


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


@pytest.fixture(scope="session")
def create_upload(
    request_json: Callable[..., tuple[int, Any]],
    api_base_url: str,
    cache_name: str,
    cache_auth_token: str,
) -> Callable[[], str]:
    """Start a multipart NAR upload on the public cache and return its narId."""

    def _create() -> str:
        status, payload = request_json(
            url=f"{api_base_url}/api/v1/cache/{cache_name}/multipart-nar?compression=xz",
            method="POST",
            headers=[f"Authorization: Bearer {cache_auth_token}"],
            data="{}",
        )
        assert status == 200
        assert isinstance(payload, dict)
        return str(payload["narId"])

    return _create


@pytest.fixture(scope="session")
def dht_values(
    request_json: Callable[..., tuple[int, Any]],
    api_base_url: str,
) -> Callable[[str], list[str]]:
    """Values the server's DHT node returns for a key (empty when none)."""

    def _get(key: str) -> list[str]:
        status, payload = request_json(f"{api_base_url}/api/v1/dht/get/{key}")
        assert status == 200
        assert isinstance(payload, dict)
        return list(payload.get("value") or [])

    return _get
