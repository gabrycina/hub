from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from hub.auth import AuthContext, can_view, get_auth, get_optional_auth
from hub.config import Settings, get_settings
from hub.db import Database, to_artifact
from hub.models import Visibility
from hub.owner import resolved_owner
from hub.report_html import enhance_report_html
from hub.storage import ArtifactStorage

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=TEMPLATES_DIR)
templates.env.auto_reload = True  # so template changes are picked without restart in dev
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


def _can_manage_artifact(
    row: dict, auth: AuthContext | None, settings: Settings
) -> bool:
    # Server (trust_network) mode: the network is the boundary — anyone who can
    # reach the dashboard can manage, mirroring open publishing.
    if settings.trust_network:
        return True
    if auth is None:
        return False
    hub_owner = resolved_owner(settings, auth)
    return auth.user == hub_owner or auth.user == row["owner"]


def _require_dashboard_access(auth: AuthContext | None, settings: Settings) -> None:
    # Local/Serve mode requires an identity to browse. In server (trust_network)
    # mode the network is the boundary, so anonymous viewers may browse — db.list
    # already limits a viewer-less listing to shareable reports.
    if auth is None and not settings.trust_network:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )


def _dashboard_context(
    *,
    auth: AuthContext | None,
    settings: Settings,
    db: Database,
    scope: str,
    q: str | None,
) -> dict:
    hub_owner = resolved_owner(settings, auth)
    # Server (trust_network) mode: the network is the access boundary, so list
    # every report to anyone who can reach it (db.list returns all when the
    # viewer is the hub owner). Local mode keeps per-viewer visibility filtering.
    # Always list all reports for the dashboard tree view (to make testing easy with the new file tree).
    # We group by project as folders.
    rows = db.list(
        viewer=hub_owner,
        hub_owner=hub_owner,
        scope="all",
        query=q,
    )
    artifacts = [to_artifact(row, settings.public_url) for row in rows]

    # Build a file-tree structure grouped by project (folders that make sense)
    # Each "file" node represents a report, with link to /a/id
    from collections import defaultdict
    by_project = defaultdict(list)
    for a in artifacts:
        proj = (a.project or "Other").strip() or "Other"
        by_project[proj].append(a)

    # Sort projects
    sorted_projects = sorted(by_project.keys())

    tree_root = {"name": "", "is_dir": True, "children": []}
    for proj in sorted_projects:
        proj_node = {
            "name": proj,
            "is_dir": True,
            "path": proj,  # not used for link
            "children": []
        }
        for a in sorted(by_project[proj], key=lambda x: x.title.lower()):
            file_node = {
                "name": a.title,
                "is_dir": False,
                "path": f"/a/{a.id}",
                "size": a.size_bytes,
                "id": a.id,
                "url": a.url,
                "title": a.title,
                "children": []
            }
            proj_node["children"].append(file_node)
        tree_root["children"].append(proj_node)

    return {
        "artifacts": artifacts,
        "scope": scope,
        "query": q or "",
        "auth": auth,
        "settings": settings,
        "hub_owner": hub_owner,
        "is_hub_owner": bool(auth and auth.user == hub_owner),
        "tree": tree_root,
    }


@router.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    scope: str = Query("all", pattern="^(mine|shared|all)$"),
    q: str | None = None,
    auth: AuthContext | None = Depends(get_optional_auth),
    settings: Settings = Depends(get_settings),
    db: Database = Depends(get_db),
) -> HTMLResponse:
    _require_dashboard_access(auth, settings)
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
    auth: AuthContext | None = Depends(get_optional_auth),
    settings: Settings = Depends(get_settings),
    db: Database = Depends(get_db),
) -> HTMLResponse:
    _require_dashboard_access(auth, settings)
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
    storage: ArtifactStorage = Depends(get_storage),
) -> HTMLResponse:
    row = db.get(artifact_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    viewer = auth.user if auth else None
    if not can_view(
        visibility=row["visibility"],
        owner=row["owner"],
        viewer=viewer,
        trust_network=settings.trust_network,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    artifact = to_artifact(row, settings.public_url)
    nested_tree = storage.get_nested_tree(artifact_id)
    flat_tree = storage.list_tree(artifact_id)
    return templates.TemplateResponse(
        request,
        "artifact.html",
        {
            "artifact": artifact,
            "auth": auth,
            "settings": settings,
            "can_manage": settings.trust_network or viewer == artifact.owner,
            "tree": nested_tree,  # keep for now if needed
            "flat_tree": flat_tree,
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
        trust_network=settings.trust_network,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    html = storage.read(artifact_id)
    if html is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    html = enhance_report_html(html)

    return HTMLResponse(
        content=html,
        headers={
            # Match iframe sandbox; allow-scripts so Mermaid/charts in reports run.
            "Content-Security-Policy": "sandbox allow-scripts allow-same-origin",
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
        trust_network=settings.trust_network,
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


def _safe_tree_path(artifacts_dir: Path, artifact_id: str, file_path: str) -> Path:
    """Resolve a path inside a report tree and ensure it cannot escape."""
    root = (artifacts_dir / artifact_id).resolve()
    candidate = (root / file_path).resolve()
    if not str(candidate).startswith(str(root)):
        raise ValueError("path traversal detected")
    # Additional guard
    try:
        if not candidate.is_relative_to(root):
            raise ValueError("path escapes tree root")
    except AttributeError:
        # Python < 3.9 fallback
        if not str(candidate).startswith(str(root)):
            raise ValueError("path escapes tree root")
    return candidate


@router.get("/a/{artifact_id}/{file_path:path}")
def serve_artifact_asset(
    artifact_id: str,
    file_path: str,
    auth: AuthContext | None = Depends(get_optional_auth),
    settings: Settings = Depends(get_settings),
    db: Database = Depends(get_db),
    storage: ArtifactStorage = Depends(get_storage),
) -> Response:
    """Serve any file inside a report's tree (images, data, extra pages, etc.).

    Auth/visibility checked the same as /raw. Placed after more specific
    routes (/raw, /download, ...) so they continue to match first.
    """
    row = db.get(artifact_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    viewer = auth.user if auth else None
    if not can_view(
        visibility=row["visibility"],
        owner=row["owner"],
        viewer=viewer,
        trust_network=settings.trust_network,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    try:
        target = _safe_tree_path(settings.artifacts_dir, artifact_id, file_path)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    return FileResponse(target)


@router.post("/a/{artifact_id}/visibility", response_class=HTMLResponse)
def toggle_visibility(
    request: Request,
    artifact_id: str,
    visibility: str = Query(..., pattern="^(private|shareable)$"),
    auth: AuthContext | None = Depends(get_optional_auth),
    settings: Settings = Depends(get_settings),
    db: Database = Depends(get_db),
) -> HTMLResponse:
    row = db.get(artifact_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if not _can_manage_artifact(row, auth, settings):
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
            "is_hub_owner": bool(auth and auth.user == hub_owner),
            "can_manage": _can_manage_artifact(updated, auth, settings),
        },
    )


@router.delete("/a/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_from_dashboard(
    artifact_id: str,
    auth: AuthContext | None = Depends(get_optional_auth),
    settings: Settings = Depends(get_settings),
    db: Database = Depends(get_db),
    storage: ArtifactStorage = Depends(get_storage),
) -> None:
    row = db.get(artifact_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if not _can_manage_artifact(row, auth, settings):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    db.delete(artifact_id)
    storage.delete(artifact_id)