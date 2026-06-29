from pathlib import Path


class ArtifactStorage:
    def __init__(self, artifacts_dir: Path):
        self.artifacts_dir = artifacts_dir
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def path_for(self, artifact_id: str) -> Path:
        return self.artifacts_dir / f"{artifact_id}.html"

    def write(self, artifact_id: str, html: str) -> int:
        path = self.path_for(artifact_id)
        path.write_text(html, encoding="utf-8")
        return len(html.encode("utf-8"))

    def read(self, artifact_id: str) -> str | None:
        path = self.path_for(artifact_id)
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    def delete(self, artifact_id: str) -> None:
        path = self.path_for(artifact_id)
        if path.exists():
            path.unlink()