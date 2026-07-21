"""Health / status router."""

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["status"])


@router.get("/status")
def api_status():
    """Return connectivity status: online/offline, last check time."""
    from rwmod.offline import get_status

    return get_status()


@router.get("/locale")
def get_locale_api():
    """Return current locale and available locales."""
    from rwmod.i18n import AVAILABLE_LOCALES, get_locale

    return {"locale": get_locale(), "available": AVAILABLE_LOCALES}


@router.post("/locale")
def set_locale_api(payload: dict):
    """Set the current locale (zh-CN or en)."""
    from rwmod.i18n import set_locale

    locale = payload.get("locale", "zh-CN")
    set_locale(locale)
    return {"ok": True, "locale": locale}


@router.get("/onboarding/check")
def onboarding_check():
    """Check what still needs configuration for first-time setup.

    Returns a list of onboarding steps with their status.
    """

    from rwmod.config import Config

    cfg = Config.load()
    steps = [
        {
            "id": "steamcmd",
            "label": "SteamCMD",
            "detail": str(cfg.steamcmd_path),
            "done": cfg.steamcmd_path.exists(),
        },
        {
            "id": "mods_dir",
            "label": "Mods 目录",
            "detail": str(cfg.mods_dir),
            "done": cfg.mods_dir.exists(),
        },
        {
            "id": "rimworld_dir",
            "label": "RimWorld 目录",
            "detail": str(cfg.rimworld_dir),
            "done": cfg.rimworld_dir.exists(),
        },
        {
            "id": "mods_installed",
            "label": "已安装 Mod",
            "detail": "",
            "done": cfg.mods_dir.exists() and any(cfg.mods_dir.iterdir()),
        },
    ]
    all_done = all(s["done"] for s in steps)
    return {"steps": steps, "all_done": all_done}

