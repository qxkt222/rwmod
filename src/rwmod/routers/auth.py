"""Auth router — login, token refresh, and protected status check."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from rwmod.auth import create_token, get_current_user

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/auth/login")
def login(payload: dict):
    """Login with shared secret to obtain a JWT token.

    Body: {"password": "your-secret"}
    Returns: {"token": "jwt-string", "expires_in": 604800}
    """
    from rwmod.auth import get_secret

    password = payload.get("password", "")
    if not password or password != get_secret():
        raise HTTPException(403, "密码错误")

    token = create_token()
    return {"token": token, "expires_in": 7 * 24 * 3600}


@router.get("/auth/verify")
def verify(user: str = Depends(get_current_user)):
    """Verify current token is valid. Returns username if valid."""
    return {"user": user, "valid": True}
