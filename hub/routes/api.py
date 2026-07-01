from datetime import datetime
import base64

from fastapi import APIRouter, Depends, HTTPException, Query, status
from nanoid import generate

from hub.auth import AuthContext, can_view, get_auth
from hub.config import Settings, get_settings
from hub.db import Database, to_artifact
from hub.models import (
    ArtifactResponse,
    CreateArtifactRequest,
    UpdateArtifactRequest,
    Visibility,
)
from hub.storage import ArtifactStorage

router = APIRouter(prefix="/api")


def get_db(settings: Settings = Depends(get_settings)) -> Database:
    return Database(settings.db_path)


def get_storage(settings: Settings = Depends(get_settings)) -> ArtifactStorage:
    return ArtifactStorage(settings.artifacts_dir)


def _require_owner(artifact: dict, auth: AuthContext) -> None:
    if artifact["owner"] != auth.user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _artifact_response(row: dict, settings: Settings) -> ArtifactResponse:
    return ArtifactResponse.from_artifact(to_artifact(row, settings.public_url))


@router.post("/artifacts", response_model=ArtifactResponse)
def create_artifact(
    payload: CreateArtifactRequest,
    auth: AuthContext = Depends(get_auth),
    settings: Settings = Depends(get_settings),
    db: Database = Depends(get_db),
    storage: ArtifactStorage = Depends(get_storage),
) -> ArtifactResponse:
    # Substitute main page html into the file tree (as index.html at root, which makes sense for the primary document).
    # This unifies everything under the new file tree storage. Existing "html" is moved over into the files structure.
    all_files = dict(payload.files or {})
    if payload.html is not None:
        all_files["index.html"] = base64.b64encode(payload.html.encode("utf-8")).decode("ascii")

    # Compute approximate total size for limit check
    total_bytes = 0
    for v in all_files.values():
        if isinstance(v, str):
            total_bytes += int(len(v) * 3 / 4)  # rough base64 decode size
        else:
            total_bytes += len(v)
    if total_bytes > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Payload exceeds {settings.max_upload_bytes} bytes",
        )

    artifact_id = generate(size=12)

    # Write all files into the tree (main html is now just "index.html" in the tree)
    for rel, content in all_files.items():
        data = base64.b64decode(content) if isinstance(content, str) else content
        storage.write_file(artifact_id, rel, data)

    # Clean legacy if any (new artifacts use tree)
    legacy = storage._legacy_path(artifact_id)
    if legacy.exists():
        legacy.unlink()

    size_bytes = storage.get_size(artifact_id)
    row = db.create(
        id=artifact_id,
        title=payload.title,
        owner=auth.user,
        visibility=payload.visibility,
        tags=payload.tags,
        project=payload.project,
        size_bytes=size_bytes,
        expires_at=payload.expires_at,
    )
    return _artifact_response(row, settings)


@router.get("/artifacts", response_model=list[ArtifactResponse])
def list_artifacts(
    scope: str = Query("all", pattern="^(mine|shared|all)$"),
    q: str | None = None,
    auth: AuthContext = Depends(get_auth),
    settings: Settings = Depends(get_settings),
    db: Database = Depends(get_db),
) -> list[ArtifactResponse]:
    rows = db.list(
        viewer=auth.user,
        hub_owner=settings.owner,
        scope=scope,
        query=q,
    )
    return [_artifact_response(row, settings) for row in rows]


@router.get("/artifacts/{artifact_id}", response_model=ArtifactResponse)
def get_artifact(
    artifact_id: str,
    auth: AuthContext = Depends(get_auth),
    settings: Settings = Depends(get_settings),
    db: Database = Depends(get_db),
) -> ArtifactResponse:
    row = db.get(artifact_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if not can_view(
        visibility=row["visibility"],
        owner=row["owner"],
        viewer=auth.user,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return _artifact_response(row, settings)


@router.patch("/artifacts/{artifact_id}", response_model=ArtifactResponse)
def update_artifact(
    artifact_id: str,
    payload: UpdateArtifactRequest,
    auth: AuthContext = Depends(get_auth),
    settings: Settings = Depends(get_settings),
    db: Database = Depends(get_db),
    storage: ArtifactStorage = Depends(get_storage),
) -> ArtifactResponse:
    row = db.get(artifact_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_owner(row, auth)

    # Substitute main page html into the file tree (as index.html).
    # html is moved over into the files structure for the tree layout.
    all_files = dict(payload.files or {})
    if payload.html is not None:
        all_files["index.html"] = base64.b64encode(payload.html.encode("utf-8")).decode("ascii")

    # Size limit (approximate) for the patch
    patch_size = 0
    for v in all_files.values():
        if isinstance(v, str):
            patch_size += int(len(v) * 3 / 4)
        else:
            patch_size += len(v)
    if patch_size > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Payload exceeds {settings.max_upload_bytes} bytes",
        )

    # Write files into the tree (main html now just another entry in the tree)
    for rel, content in all_files.items():
        data = base64.b64decode(content) if isinstance(content, str) else content
        storage.write_file(artifact_id, rel, data)

    # Clean any legacy single-file html now that we're using the tree
    if all_files:
        legacy = storage._legacy_path(artifact_id)
        if legacy.exists():
            legacy.unlink()

    size_bytes = storage.get_size(artifact_id) if all_files else None

    updated = db.update(
        artifact_id,
        title=payload.title,
        visibility=payload.visibility,
        tags=payload.tags,
        project=payload.project,
        size_bytes=size_bytes,
    )
    assert updated is not None
    return _artifact_response(updated, settings)


@router.delete("/artifacts/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_artifact(
    artifact_id: str,
    auth: AuthContext = Depends(get_auth),
    db: Database = Depends(get_db),
    storage: ArtifactStorage = Depends(get_storage),
) -> None:
    row = db.get(artifact_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_owner(row, auth)
    db.delete(artifact_id)
    storage.delete(artifact_id)