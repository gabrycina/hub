from datetime import datetime

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
    if len(payload.html.encode("utf-8")) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"HTML exceeds {settings.max_upload_bytes} bytes",
        )

    artifact_id = generate(size=12)
    size_bytes = storage.write(artifact_id, payload.html)
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
) -> ArtifactResponse:
    row = db.get(artifact_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_owner(row, auth)
    updated = db.update(
        artifact_id,
        title=payload.title,
        visibility=payload.visibility,
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