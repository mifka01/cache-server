#!/usr/bin/env python3.12
"""
validation

Validation of client-supplied store path metadata before it reaches storage or narinfo text.
"""

import re
from dataclasses import dataclass

# Nix base32 omits e, o, t and u; store path hashes are always 32 characters long.
STORE_HASH_RE = re.compile(r"[0-9a-df-np-sv-z]{32}")
# Store path names: no leading dot, restricted character set (see Nix's checkName).
STORE_NAME_RE = re.compile(r"(?!\.)[0-9A-Za-z+\-._?=]{1,211}")
# Compressed NAR file hash, used as a file name; base16 or base32.
FILE_HASH_RE = re.compile(r"[0-9a-z]{1,128}")
# NAR hash as written to narinfo, e.g. "sha256:<base32>".
NAR_HASH_RE = re.compile(r"[a-z0-9]+:[0-9A-Za-z+/=]{1,128}")


@dataclass(frozen=True)
class NarInfoCreate:
    """Validated `narInfoCreate` payload of a completed multipart upload."""

    store_hash: str
    store_suffix: str
    file_hash: str
    file_size: int
    nar_hash: str
    nar_size: int
    deriver: str
    references: list[str]


def _matching_str(data: dict[str, object], key: str, pattern: re.Pattern[str]) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ValueError(f"invalid {key}")
    return value


def _size(data: dict[str, object], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"invalid {key}")
    return value


def _reference(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("invalid cReferences")
    store_hash, separator, name = value.partition("-")
    if not separator or not STORE_HASH_RE.fullmatch(store_hash) or not STORE_NAME_RE.fullmatch(name):
        raise ValueError("invalid cReferences")
    return value


def parse_narinfo_create(data: object) -> NarInfoCreate:
    """Validate a `narInfoCreate` object; raises ValueError naming the first invalid field."""
    if not isinstance(data, dict):
        raise ValueError("missing narInfoCreate")

    deriver = data.get("cDeriver", "")
    if not isinstance(deriver, str) or (deriver and not STORE_NAME_RE.fullmatch(deriver)):
        raise ValueError("invalid cDeriver")

    references = data.get("cReferences", [])
    if not isinstance(references, list):
        raise ValueError("invalid cReferences")

    return NarInfoCreate(
        store_hash=_matching_str(data, "cStoreHash", STORE_HASH_RE),
        store_suffix=_matching_str(data, "cStoreSuffix", STORE_NAME_RE),
        file_hash=_matching_str(data, "cFileHash", FILE_HASH_RE),
        file_size=_size(data, "cFileSize"),
        nar_hash=_matching_str(data, "cNarHash", NAR_HASH_RE),
        nar_size=_size(data, "cNarSize"),
        deriver=deriver,
        references=[_reference(reference) for reference in references],
    )
