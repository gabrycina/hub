from datetime import datetime
from enum import Enum
from typing import Self

from pydantic import BaseModel, Field


class Visibility(str, Enum):
    PRIVATE = "private"
    SHAREABLE = "shareable"


class Artifact(BaseModel):
    id: str
    title: str
    owner: str
    visibility: Visibility
    tags: list[str] = Field(default_factory=list)
    project: str | None = None
    size_bytes: int
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None = None
    url: str | None = None

    @classmethod
    def from_row(cls, row: dict, public_url: str) -> Self:
        data = dict(row)
        data["tags"] = __import__("json").loads(data.get("tags") or "[]")
        data["visibility"] = Visibility(data["visibility"])
        for field in ("created_at", "updated_at", "expires_at"):
            if data.get(field):
                data[field] = datetime.fromisoformat(data[field])
        artifact = cls(**data)
        artifact.url = f"{public_url.rstrip('/')}/a/{artifact.id}"
        return artifact


class CreateArtifactRequest(BaseModel):
    # html is substituted into the file tree as "index.html" (root of the artifact tree).
    # This moves the main page HTML over into the new file tree layout (in the folder that makes sense: root index.html).
    # Kept for backward compat; prefer providing "index.html" (or other main) inside `files`.
    html: str | None = None
    title: str
    visibility: Visibility = Visibility.PRIVATE
    tags: list[str] = Field(default_factory=list)
    project: str | None = None
    expires_at: datetime | None = None
    # files for the report tree: relpath -> base64 content. Main page can be "index.html" here.
    files: dict[str, str] | None = None


class UpdateArtifactRequest(BaseModel):
    title: str | None = None
    visibility: Visibility | None = None
    # html is substituted into the file tree as "index.html" (moving main page over into tree).
    # Kept for backward compat.
    html: str | None = None
    tags: list[str] | None = None
    project: str | None = None
    # files for the report tree (updates/adds to tree)
    files: dict[str, str] | None = None


class ArtifactResponse(BaseModel):
    id: str
    title: str
    owner: str
    visibility: Visibility
    tags: list[str]
    project: str | None
    size_bytes: int
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None
    url: str

    @classmethod
    def from_artifact(cls, artifact: Artifact) -> Self:
        return cls(
            id=artifact.id,
            title=artifact.title,
            owner=artifact.owner,
            visibility=artifact.visibility,
            tags=artifact.tags,
            project=artifact.project,
            size_bytes=artifact.size_bytes,
            created_at=artifact.created_at,
            updated_at=artifact.updated_at,
            expires_at=artifact.expires_at,
            url=artifact.url or "",
        )