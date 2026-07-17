"""Pydantic response models — shared across all routers."""

from __future__ import annotations

# Re-export commonly used response shapes.
# Each router may define its own models for specific payloads,
# but these are the shared ones used by multiple endpoints.
from pydantic import BaseModel


class OkResponse(BaseModel):
    """Generic success response."""

    ok: bool = True


class ErrorResponse(BaseModel):
    """Generic error response."""

    detail: str
