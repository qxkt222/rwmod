"""Auto-update router — background update check and manual trigger."""

from fastapi import APIRouter, Depends

from rwmod.autoupdate import AutoUpdateManager
from rwmod.deps import get_autoupdate

router = APIRouter(prefix="/api", tags=["auto-update"])


@router.get("/auto-check/result")
def auto_check_result(au: AutoUpdateManager = Depends(get_autoupdate)):
    return {"updates": au.last_result, "count": len(au.last_result)}


@router.post("/auto-check/clear")
def auto_check_clear(au: AutoUpdateManager = Depends(get_autoupdate)):
    au.clear_result()
    return {"ok": True}


@router.get("/auto-update/status")
def auto_update_status(au: AutoUpdateManager = Depends(get_autoupdate)):
    return {"running": au.is_running}


@router.post("/auto-update/run")
async def auto_update_run(au: AutoUpdateManager = Depends(get_autoupdate)):
    return await au.run_check()
