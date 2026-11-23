#!/usr/bin/env python3.12
"""
validation

Validation of client-supplied store path metadata before it reaches storage or narinfo text.
"""

import re
from dataclasses import dataclass

# Nix base32 omits e, o, t and u; store path hashes are always 32 characters long.
STORE_HASH_RE = re.compile(r"[0-9a-df-np-sv-z]{32}")
# Store path names (Nix's checkName): restricted character set; ".", ".." and names
# starting with ".-" or "..-" are invalid, other dot-leading names such as ".zshrc" are fine.
STORE_NAME_RE = re.compile(r"(?!\.\.?(?:-|$))[0-9A-Za-z+\-._?=]{1,211}")
# SHA-256 of the compressed NAR, used as a file name: base16 or Nix base32.
FILE_HASH_RE = re.compile(r"[0-9a-f]{64}|[0-9a-df-np-sv-z]{52}")
# NAR hash as written to narinfo, e.g. "sha256:<base32>".
NAR_HASH_RE = re.compile(r"[a-z0-9]+:[0-9A-Za-z+/=]{1,128}")
# S3, whose multipart protocol cachix follows, allows parts 1 to 10000.
MAX_PART_NUMBER = 10000


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


def _is_store_basename(value: object) -> bool:
    """True for `<hash>-<name>`, the store path base name Nix uses in narinfo references and derivers."""
    if not isinstance(value, str):
        return False
    store_hash, separator, name = value.partition("-")
    return bool(separator) and bool(STORE_HASH_RE.fullmatch(store_hash)) and bool(STORE_NAME_RE.fullmatch(name))


def _reference(value: object) -> str:
    if not isinstance(value, str) or not _is_store_basename(value):
        raise ValueError("invalid cReferences")
    return value


def parse_narinfo_create(data: object) -> NarInfoCreate:
    """Validate a `narInfoCreate` object; raises ValueError naming the first invalid field."""
    if not isinstance(data, dict):
        raise ValueError("missing narInfoCreate")

    deriver = data.get("cDeriver")
    is_derivation = isinstance(deriver, str) and deriver.endswith(".drv") and _is_store_basename(deriver)
    if not isinstance(deriver, str) or (deriver != "unknown-deriver" and not is_derivation):
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


def parse_part_number(value: str | None) -> int:
    """Validate the `partNumber` of a multipart upload part (1-based, as in S3 and cachix)."""
    if value is None or not value.isdigit() or not 1 <= int(value) <= MAX_PART_NUMBER:
        raise ValueError("invalid partNumber")
    return int(value)


def parse_completed_parts(data: object) -> list[tuple[int, str]]:
    """Validate the `parts` of a completed upload; returns (partNumber, eTag) pairs in part order."""
    if not isinstance(data, list) or not data:
        raise ValueError("missing parts")

    parts = []
    for part in data:
        if not isinstance(part, dict):
            raise ValueError("invalid parts")
        number, tag = part.get("partNumber"), part.get("eTag")
        if not isinstance(number, int) or isinstance(number, bool) or not 1 <= number <= MAX_PART_NUMBER:
            raise ValueError("invalid partNumber in parts")
        if not isinstance(tag, str):
            raise ValueError("invalid eTag in parts")
        parts.append((number, tag))

    parts.sort()
    if len({number for number, _ in parts}) != len(parts):
        raise ValueError("duplicate partNumber in parts")
    return parts
