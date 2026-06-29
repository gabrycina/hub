import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from hub.models import Artifact, Visibility


class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def connection(self):
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    visibility TEXT NOT NULL,
                    tags TEXT NOT NULL DEFAULT '[]',
                    project TEXT,
                    size_bytes INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    expires_at TEXT
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_artifacts_owner ON artifacts(owner)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_artifacts_visibility ON artifacts(visibility)"
            )

    def create(
        self,
        *,
        id: str,
        title: str,
        owner: str,
        visibility: Visibility,
        tags: list[str],
        project: str | None,
        size_bytes: int,
        expires_at: datetime | None,
    ) -> dict:
        now = datetime.now(UTC).isoformat()
        expires = expires_at.isoformat() if expires_at else None
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO artifacts (
                    id, title, owner, visibility, tags, project,
                    size_bytes, created_at, updated_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    id,
                    title,
                    owner,
                    visibility.value,
                    json.dumps(tags),
                    project,
                    size_bytes,
                    now,
                    now,
                    expires,
                ),
            )
        return self.get(id)

    def get(self, artifact_id: str) -> dict | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM artifacts WHERE id = ?", (artifact_id,)
            ).fetchone()
        return dict(row) if row else None

    def list(
        self,
        *,
        viewer: str | None,
        hub_owner: str,
        scope: str = "all",
        query: str | None = None,
    ) -> list[dict]:
        clauses: list[str] = []
        params: list[object] = []

        if scope == "mine":
            if not viewer:
                return []
            clauses.append("owner = ?")
            params.append(viewer)
        elif scope == "shared":
            clauses.append("visibility = ?")
            params.append(Visibility.SHAREABLE.value)
        elif scope == "all":
            if viewer == hub_owner:
                pass
            elif viewer:
                clauses.append(
                    "(visibility = ? OR owner = ?)"
                )
                params.extend([Visibility.SHAREABLE.value, viewer])
            else:
                clauses.append("visibility = ?")
                params.append(Visibility.SHAREABLE.value)

        if query:
            clauses.append("(title LIKE ? OR tags LIKE ? OR project LIKE ?)")
            pattern = f"%{query}%"
            params.extend([pattern, pattern, pattern])

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT * FROM artifacts {where} ORDER BY created_at ASC"

        with self.connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def update(
        self,
        artifact_id: str,
        *,
        title: str | None = None,
        visibility: Visibility | None = None,
    ) -> dict | None:
        existing = self.get(artifact_id)
        if not existing:
            return None

        fields: list[str] = []
        params: list[object] = []

        if title is not None:
            fields.append("title = ?")
            params.append(title)
        if visibility is not None:
            fields.append("visibility = ?")
            params.append(visibility.value)

        if not fields:
            return existing

        fields.append("updated_at = ?")
        params.append(datetime.now(UTC).isoformat())
        params.append(artifact_id)

        with self.connection() as conn:
            conn.execute(
                f"UPDATE artifacts SET {', '.join(fields)} WHERE id = ?",
                params,
            )
        return self.get(artifact_id)

    def delete(self, artifact_id: str) -> bool:
        with self.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM artifacts WHERE id = ?", (artifact_id,)
            )
        return cursor.rowcount > 0


def to_artifact(row: dict, public_url: str) -> Artifact:
    return Artifact.from_row(row, public_url)