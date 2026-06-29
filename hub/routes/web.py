from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from hub.auth import AuthContext, can_view, get_auth, get_optional_auth
from hub.config import Settings, get_settings
from hub.db import Database, to_artifact
from hub.models import Visibility
from hub.owner import resolved_owner
from hub.storage import ArtifactStorage

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=TEMPLATES_DIR)
router = APIRouter()


def get_db(settings: Settings = Depends(get_settings)) -> Database:
    return Database(settings.db_path)


def get_storage(settings: Settings = Depends(get_settings)) -> ArtifactStorage:
    return ArtifactStorage(settings.artifacts_dir)


def _format_bytes(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


templates.env.filters["format_bytes"] = _format_bytes


def _dashboard_context(
    *,
    auth: AuthContext,
    settings: Settings,
    db: Database,
    scope: str,
    q: str | None,
) -> dict:
    hub_owner = resolved_owner(settings, auth)
    rows = db.list(
        viewer=auth.user,
        hub_owner=hub_owner,
        scope=scope,
        query=q,
    )
    artifacts = [to_artifact(row, settings.public_url) for row in rows]
    return {
        "artifacts": artifacts,
        "scope": scope,
        "query": q or "",
        "auth": auth,
        "settings": settings,
        "hub_owner": hub_owner,
        "is_hub_owner": auth.user == hub_owner,
    }


@router.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    scope: str = Query("all", pattern="^(mine|shared|all)$"),
    q: str | None = None,
    auth: AuthContext = Depends(get_auth),
    settings: Settings = Depends(get_settings),
    db: Database = Depends(get_db),
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        _dashboard_context(auth=auth, settings=settings, db=db, scope=scope, q=q),
    )


@router.get("/partials/reports", response_class=HTMLResponse)
def reports_partial(
    request: Request,
    scope: str = Query("all", pattern="^(mine|shared|all)$"),
    q: str | None = None,
    auth: AuthContext = Depends(get_auth),
    settings: Settings = Depends(get_settings),
    db: Database = Depends(get_db),
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "partials/artifact_list.html",
        _dashboard_context(auth=auth, settings=settings, db=db, scope=scope, q=q),
    )


@router.get("/a/{artifact_id}", response_class=HTMLResponse)
def preview_artifact(
    request: Request,
    artifact_id: str,
    auth: AuthContext | None = Depends(get_optional_auth),
    settings: Settings = Depends(get_settings),
    db: Database = Depends(get_db),
) -> HTMLResponse:
    row = db.get(artifact_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    viewer = auth.user if auth else None
    if not can_view(
        visibility=row["visibility"],
        owner=row["owner"],
        viewer=viewer,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    artifact = to_artifact(row, settings.public_url)
    return templates.TemplateResponse(
        request,
        "artifact.html",
        {
            "artifact": artifact,
            "auth": auth,
            "settings": settings,
            "can_manage": viewer == artifact.owner,
        },
    )


@router.get("/a/{artifact_id}/raw")
def raw_artifact(
    artifact_id: str,
    auth: AuthContext | None = Depends(get_optional_auth),
    settings: Settings = Depends(get_settings),
    db: Database = Depends(get_db),
    storage: ArtifactStorage = Depends(get_storage),
) -> Response:
    row = db.get(artifact_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    viewer = auth.user if auth else None
    if not can_view(
        visibility=row["visibility"],
        owner=row["owner"],
        viewer=viewer,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    html = storage.read(artifact_id)
    if html is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    return HTMLResponse(
        content=html,
        headers={
            "Content-Security-Policy": "sandbox",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/a/{artifact_id}/download")
def download_artifact(
    artifact_id: str,
    auth: AuthContext | None = Depends(get_optional_auth),
    settings: Settings = Depends(get_settings),
    db: Database = Depends(get_db),
    storage: ArtifactStorage = Depends(get_storage),
) -> FileResponse:
    row = db.get(artifact_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    viewer = auth.user if auth else None
    if not can_view(
        visibility=row["visibility"],
        owner=row["owner"],
        viewer=viewer,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    path = storage.path_for(artifact_id)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    safe_title = "".join(
        char if char.isalnum() or char in ("-", "_") else "-"
        for char in row["title"].lower()
    )
    return FileResponse(
        path,
        media_type="text/html",
        filename=f"{safe_title or artifact_id}.html",
    )


@router.post("/a/{artifact_id}/visibility", response_class=HTMLResponse)
def toggle_visibility(
    request: Request,
    artifact_id: str,
    visibility: str = Query(..., pattern="^(private|shareable)$"),
    auth: AuthContext = Depends(get_auth),
    settings: Settings = Depends(get_settings),
    db: Database = Depends(get_db),
) -> HTMLResponse:
    row = db.get(artifact_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if row["owner"] != auth.user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    updated = db.update(artifact_id, visibility=Visibility(visibility))
    assert updated is not None
    artifact = to_artifact(updated, settings.public_url)

    hub_owner = resolved_owner(settings, auth)
    return templates.TemplateResponse(
        request,
        "partials/artifact_row.html",
        {
            "artifact": artifact,
            "auth": auth,
            "settings": settings,
            "hub_owner": hub_owner,
            "is_hub_owner": auth.user == hub_owner,
            "can_manage": True,
        },
    )


@router.delete("/a/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_from_dashboard(
    artifact_id: str,
    auth: AuthContext = Depends(get_auth),
    db: Database = Depends(get_db),
    storage: ArtifactStorage = Depends(get_storage),
) -> None:
    row = db.get(artifact_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if row["owner"] != auth.user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    db.delete(artifact_id)
    storage.delete(artifact_id)