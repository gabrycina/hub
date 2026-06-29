from hub.auth import AuthContext
from hub.bootstrap import detect_owner
from hub.config import Settings

_STALE_OWNERS = {"", "local@dev"}


def resolved_owner(settings: Settings, auth: AuthContext | None = None) -> str:
    """Return the effective hub owner, falling back from stale config."""
    if settings.owner and settings.owner not in _STALE_OWNERS:
        return settings.owner

    detected = detect_owner()
    if detected and detected not in _STALE_OWNERS:
        return detected

    if auth and auth.user and auth.user not in _STALE_OWNERS:
        return auth.user

    return settings.owner or "local@dev"