from hub.bootstrap import detect_owner
from hub.config import Settings


def resolved_owner(settings: Settings) -> str:
    """Return the effective hub owner, falling back from stale local@dev config."""
    if settings.owner and settings.owner != "local@dev":
        return settings.owner
    detected = detect_owner()
    if detected and detected != "local@dev":
        return detected
    return settings.owner