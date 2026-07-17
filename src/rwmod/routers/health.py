"""Health / status router."""

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["status"])


@router.get("/status")
def api_status():
    """Return connectivity status: online/offline, last check time."""
    from rwmod.offline import get_status

    return get_status()
