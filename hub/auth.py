from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from hub.config import Settings, get_settings

TAILSCALE_USER_HEADER = "Tailscale-User-Login"
LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient"}
security = HTTPBearer(auto_error=False)


@dataclass
class AuthContext:
    user: str
    is_owner: bool
    via_token: bool


def _client_host(request: Request) -> str:
    if request.client:
        return request.client.host
    return ""


def _is_local_request(request: Request) -> bool:
    return _client_host(request) in LOCAL_HOSTS


def can_view(
    *,
    visibility: str,
    owner: str,
    viewer: str | None,
    trust_network: bool = False,
) -> bool:
    if visibility == "shareable":
        # In server (trust_network) mode the network is the access boundary, so a
        # shareable report is viewable even without an identified viewer.
        return trust_network or viewer is not None
    return viewer == owner


def resolve_user(
    request: Request,
    settings: Settings,
    credentials: HTTPAuthorizationCredentials | None,
) -> AuthContext | None:
    if request.url.path == "/health":
        return None

    if credentials and credentials.credentials:
        if not settings.api_token:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="API token not configured",
            )
        if credentials.credentials != settings.api_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API token",
            )
        return AuthContext(
            user=settings.owner,
            is_owner=True,
            via_token=True,
        )

    tailscale_user = request.headers.get(TAILSCALE_USER_HEADER)
    if tailscale_user:
        # Serve injects identity headers when proxying to localhost.
        # Direct callers on the same machine could spoof headers — mitigated
        # by binding Hub to 127.0.0.1 only (see docs/security.md).
        return AuthContext(
            user=tailscale_user,
            is_owner=tailscale_user == settings.owner,
            via_token=False,
        )

    if settings.dev_user and _is_local_request(request):
        return AuthContext(
            user=settings.dev_user,
            is_owner=settings.dev_user == settings.owner,
            via_token=False,
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
    )


async def get_auth(
    request: Request,
    settings: Settings = Depends(get_settings),
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> AuthContext:
    auth = resolve_user(request, settings, credentials)
    if auth is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return auth


async def get_optional_auth(
    request: Request,
    settings: Settings = Depends(get_settings),
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> AuthContext | None:
    if request.url.path == "/health":
        return None
    try:
        return resolve_user(request, settings, credentials)
    except HTTPException:
        return None