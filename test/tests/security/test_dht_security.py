from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Callable, Iterator

import pytest


def _wait_until(condition: Callable[[], bool], attempts: int = 40, delay: float = 0.5) -> bool:
    for _ in range(attempts):
        if condition():
            return True
        time.sleep(delay)
    return False


@pytest.mark.security
def test_dht_put_requires_cache_token(
    require_api_endpoint: None,
    http_request: Callable[..., tuple[int, str]],
    api_base_url: str,
) -> None:
    del require_api_endpoint
    body = json.dumps({"key": "qa-dht-unauthenticated", "value": "x", "permanent": False})

    status, _ = http_request(
        url=f"{api_base_url}/api/v1/dht/put",
        method="POST",
        headers=["Content-Type: application/json"],
        data=body,
    )
    assert status == 401

    status, _ = http_request(
        url=f"{api_base_url}/api/v1/dht/put",
        method="POST",
        headers=["Authorization: Bearer invalid-token", "Content-Type: application/json"],
        data=body,
    )
    assert status == 401


@pytest.mark.security
@pytest.mark.requires_token
def test_cache_advertisement_does_not_leak_token(
    require_api_endpoint: None,
    require_cache_token: None,
    dht_values: Callable[[str], list[str]],
    cache_id: str,
    cache_auth_token: str,
) -> None:
    del require_api_endpoint, require_cache_token
    values: list[str] = []

    def advertised() -> bool:
        values[:] = dht_values(cache_id)
        return bool(values)

    assert _wait_until(advertised), "public cache is not advertised in the DHT"
    for value in values:
        assert cache_auth_token not in value
        assert "token" not in json.loads(value)


@pytest.fixture
def fake_peer(tmp_path: Path) -> Iterator[tuple[str, Path]]:
    """Plain HTTP binary cache on the client that only the DHT points to."""
    port = int(os.environ.get("QA_FAKE_PEER_PORT", "8099"))
    (tmp_path / "nix-cache-info").write_text("StoreDir: /nix/store\nWantMassQuery: 1\nPriority: 30\n")
    process = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind", "0.0.0.0", "--directory", str(tmp_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        local_url = f"http://127.0.0.1:{port}/nix-cache-info"
        ready = _wait_until(
            lambda: subprocess.run(["curl", "-fsS", "--max-time", "2", local_url], capture_output=True).returncode == 0
        )
        assert ready, "fake peer did not start"
        yield f"http://{socket.gethostname()}:{port}", tmp_path
    finally:
        process.terminate()
        process.wait(timeout=10)


@pytest.mark.security
@pytest.mark.requires_token
def test_remote_narinfo_is_not_signed_with_cache_key(
    require_api_endpoint: None,
    require_nix_cache_endpoint: None,
    require_cache_token: None,
    fake_peer: tuple[str, Path],
    get_json: Callable[[str], dict],
    http_request: Callable[..., tuple[int, str]],
    dht_values: Callable[[str], list[str]],
    random_nix_hash: Callable[[int], str],
    api_base_url: str,
    nix_cache_url: str,
    cache_name: str,
    cache_auth_token: str,
) -> None:
    """A narinfo found through the DHT comes from an untrusted peer and must not get this cache's signature."""
    del require_api_endpoint, require_nix_cache_endpoint, require_cache_token
    peer_url, peer_root = fake_peer

    store_hash = random_nix_hash(32)
    file_hash = random_nix_hash(52)
    (peer_root / f"{store_hash}.narinfo").write_text(
        f"StorePath: /nix/store/{store_hash}-qa-injected\n"
        f"URL: nar/{file_hash}.nar.xz\n"
        "Compression: xz\n"
        f"FileHash: sha256:{file_hash}\n"
        "FileSize: 4\n"
        f"NarHash: sha256:{random_nix_hash(52)}\n"
        "NarSize: 4\n"
        "References: \n"
        "Deriver: unknown-deriver\n"
    )

    peer_id = f"qa-fake-peer-{uuid.uuid4()}"
    peer_info = json.dumps({"id": peer_id, "url": peer_url, "metrics": {"load_score": 0}})
    for key, value in ((store_hash, peer_id), (peer_id, peer_info)):
        status, _ = http_request(
            url=f"{api_base_url}/api/v1/dht/put",
            method="POST",
            headers=[f"Authorization: Bearer {cache_auth_token}", "Content-Type: application/json"],
            data=json.dumps({"key": key, "value": value, "permanent": False}),
        )
        assert status == 200

    assert _wait_until(lambda: peer_id in dht_values(store_hash) and bool(dht_values(peer_id))), (
        "injected peer is not visible in the DHT"
    )

    signing_key = get_json(f"{api_base_url}/api/v1/cache/{cache_name}?")["publicSigningKeys"][0]
    key_name = signing_key.split(":", 1)[0]

    status, narinfo = http_request(f"{nix_cache_url}/{store_hash}.narinfo")
    assert status == 200, "narinfo of a DHT peer should be served unmodified"
    assert f"Sig: {key_name}:" not in narinfo
    assert f"StorePath: /nix/store/{store_hash}-qa-injected" in narinfo
