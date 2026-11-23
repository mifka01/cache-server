#!/usr/bin/env python3.12
"""
auth

Token generation and HTTP credential checks shared by the APIs.
"""

import base64
import binascii
import hmac
import secrets

TOKEN_BYTES = 32


def generate_token() -> str:
    """Return a new random, unguessable access token."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def is_legacy_token(token: str) -> bool:
    """Tokens of older versions were JWTs derived from the entity name and the server key."""
    return "." in token


def tokens_match(provided: str | None, expected: str) -> bool:
    """Compare tokens in constant time; a missing token never matches."""
    if not provided or not expected:
        return False
    return hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))


def bearer_token(authorization: str | None) -> str | None:
    """Extract the token from an `Authorization: Bearer <token>` header value."""
    if not authorization:
        return None
    scheme, _, token = authorization.strip().partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def basic_auth_password(authorization: str | None) -> str | None:
    """Extract the password from an `Authorization: Basic <base64(user:password)>` header value."""
    if not authorization:
        return None
    scheme, _, encoded = authorization.strip().partition(" ")
    if scheme.lower() != "basic":
        return None
    try:
        decoded = base64.b64decode(encoded.strip(), validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return None
    _, separator, password = decoded.partition(":")
    return password if separator else None
