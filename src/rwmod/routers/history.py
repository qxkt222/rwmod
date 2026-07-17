"""History router."""

from fastapi import APIRouter

from rwmod.database import clear_history, get_download_history, get_download_stats

router = APIRouter(prefix="/api", tags=["history"])


@router.get("/history")
def history(limit: int = 50, status: str = ""):
    return {"items": get_download_history(limit=limit, status=status)}


@router.get("/history/stats")
def history_stats():
    return get_download_stats()


@router.post("/history/clear")
def history_clear():
    clear_history()
    return {"ok": True}
