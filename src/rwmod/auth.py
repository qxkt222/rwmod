"""JWT authentication for rwmod.

Simple token-based auth: login with a shared secret to get a JWT bearer token.
All protected endpoints verify the token via FastAPI dependency.

Config:
    Set RWMOD_SECRET env var for the signing key.
    Default: "rwmod-dev-secret" (NOT for production).

Usage in routers:
    from rwmod.auth import get_current_user
    @router.get("/protected")
    def protected_endpoint(user: str = Depends(get_current_user)):
        ...
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from base64 import urlsafe_b64encode

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

__all__ = ["create_token", "verify_token", "get_current_user", "get_secret"]

_security = HTTPBearer(auto_error=False)
_TOKEN_VERSION = 1
_TOKEN_TTL = 7 * 24 * 3600  # 7 days


def get_secret() -> str:
    """Get the signing secret from env or default."""
    return os.environ.get("RWMOD_SECRET", "rwmod-dev-secret")


def _hmac_sign(payload: bytes, secret: str) -> bytes:
    return hmac.new(secret.encode(), payload, hashlib.sha256).digest()


def create_token(username: str = "admin") -> str:
    """Create a JWT-like token (simplified — HMAC-SHA256 over JSON payload).

    Format: base64(header).base64(payload).base64(signature)
    """
    header = urlsafe_b64encode(
        json.dumps({"alg": "HS256", "typ": "JWT", "ver": _TOKEN_VERSION}).encode()
    ).rstrip(b"=")

    exp = int(time.time()) + _TOKEN_TTL
    payload = urlsafe_b64encode(
        json.dumps({"sub": username, "iat": int(time.time()), "exp": exp}).encode()
    ).rstrip(b"=")

    signing_input = header + b"." + payload
    sig = urlsafe_b64encode(_hmac_sign(signing_input, get_secret())).rstrip(b"=")

    return f"{header.decode()}.{payload.decode()}.{sig.decode()}"


def verify_token(token: str) -> str | None:
    """Verify a token and return the username if valid. Returns None if invalid."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, sig_b64 = parts

        # Verify signature
        signing_input = f"{header_b64}.{payload_b64}".encode()
        expected_sig = (
            urlsafe_b64encode(_hmac_sign(signing_input, get_secret()))
            .rstrip(b"=")
            .decode()
        )

        if not hmac.compare_digest(sig_b64, expected_sig):
            return None

        # Decode payload
        payload_bytes = _b64_decode(payload_b64)
        payload = json.loads(payload_bytes)

        # Check expiration
        if payload.get("exp", 0) < time.time():
            return None

        return payload.get("sub")
    except Exception:
        return None


def _b64_decode(s: str) -> bytes:
    """URL-safe base64 decode with padding fix."""
    import base64

    s = s + "=" * (4 - len(s) % 4) if len(s) % 4 else s
    return base64.urlsafe_b64decode(s)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),  # noqa: B008
) -> str:
    """FastAPI dependency: extract and verify JWT from Authorization header.

    Skips auth entirely if the secret is the default (dev mode).
    """
    # Dev mode: skip auth with default secret
    if get_secret() == "rwmod-dev-secret":
        return "admin"

    if credentials is None:
        raise HTTPException(401, "需要认证", headers={"WWW-Authenticate": "Bearer"})

    user = verify_token(credentials.credentials)
    if user is None:
        raise HTTPException(401, "Token 无效或已过期", headers={"WWW-Authenticate": "Bearer"})

    return user
