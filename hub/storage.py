from pathlib import Path

import fsspec


class ArtifactStorage:
    """Storage for report artifacts.

    Uses a per-report directory tree layout:
      artifacts/{id}/index.html   # the main page HTML (substituted from `html` param or provided in `files`)
      artifacts/{id}/(any additional files or subdirs)

    The old single-file layout ({id}.html) is still readable for backward compat
    (legacy reports continue to work until overwritten).
    Main page HTMLs are substituted/moved over into the tree as index.html .
    """

    PRIMARY = "index.html"

    def __init__(self, artifacts_dir: Path):
        self.artifacts_dir = artifacts_dir
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.fs = fsspec.filesystem("file")

    def _root(self, artifact_id: str) -> str:
        return str(self.artifacts_dir / artifact_id)

    def _primary_path(self, artifact_id: str) -> str:
        return str(self.artifacts_dir / artifact_id / self.PRIMARY)

    def _legacy_path(self, artifact_id: str) -> Path:
        return self.artifacts_dir / f"{artifact_id}.html"

    def path_for(self, artifact_id: str) -> Path:
        """Return path to primary document (for download etc.).

        Prefers the tree primary; falls back to legacy single file.
        """
        p = self.artifacts_dir / artifact_id / self.PRIMARY
        if p.exists():
            return p
        legacy = self._legacy_path(artifact_id)
        if legacy.exists():
            return legacy
        return p

    def _sanitize_rel(self, rel_path: str) -> str:
        if not rel_path or rel_path.startswith("/") or ".." in rel_path.split("/"):
            raise ValueError(f"Invalid rel_path: {rel_path}")
        # normalize away ./ etc.
        return rel_path.lstrip("./")

    def write(self, artifact_id: str, html: str) -> int:
        """Write the primary document (compat with old single-html callers).

        Stores as {id}/index.html inside a per-report tree.
        Also removes any legacy {id}.html for the same id.
        Returns size in bytes of the written content.
        """
        data = html.encode("utf-8")
        size = self.write_file(artifact_id, self.PRIMARY, data)
        # Clean legacy single file if present
        legacy = self._legacy_path(artifact_id)
        if legacy.exists():
            legacy.unlink()
        return size

    def write_file(self, artifact_id: str, rel_path: str, data: bytes) -> int:
        """Write (or overwrite) an arbitrary file inside the report's tree.

        Creates parent directories as needed. Returns bytes written.
        """
        rel = self._sanitize_rel(rel_path)
        root = self._root(artifact_id)
        self.fs.makedirs(root, exist_ok=True)

        # Ensure parent dir for the file
        parent = str(Path(root) / Path(rel).parent)
        if parent != root:
            self.fs.makedirs(parent, exist_ok=True)

        full = f"{root}/{rel}"
        self.fs.pipe_file(full, data)
        return len(data)

    def read(self, artifact_id: str) -> str | None:
        """Read the primary document as text (for /raw etc.).

        Tries tree primary first, then legacy single file.
        """
        p = self._primary_path(artifact_id)
        if self.fs.exists(p):
            return self.fs.cat_file(p).decode("utf-8")
        legacy = self._legacy_path(artifact_id)
        if legacy.exists():
            return legacy.read_text(encoding="utf-8")
        return None

    def read_file(self, artifact_id: str, rel_path: str) -> bytes | None:
        """Read an arbitrary file from the report tree as bytes."""
        rel = self._sanitize_rel(rel_path)
        full = f"{self._root(artifact_id)}/{rel}"
        if not self.fs.exists(full):
            return None
        return self.fs.cat_file(full)

    def get_size(self, artifact_id: str) -> int:
        """Total size in bytes of the report tree (or legacy file)."""
        root = self._root(artifact_id)
        if self.fs.exists(root):
            total = 0
            for p in self.fs.find(root, withdirs=False):
                try:
                    total += self.fs.size(p) or 0
                except Exception:
                    pass
            return total
        legacy = self._legacy_path(artifact_id)
        if legacy.exists():
            return legacy.stat().st_size
        return 0

    def delete(self, artifact_id: str) -> None:
        """Delete the entire report tree (or legacy single file)."""
        root = self._root(artifact_id)
        if self.fs.exists(root):
            self.fs.rm(root, recursive=True)
        legacy = self._legacy_path(artifact_id)
        if legacy.exists():
            legacy.unlink()

    def list_tree(self, artifact_id: str) -> list[dict]:
        """Return sorted list of entries in the report's file tree.

        Each item: {"path": "foo/bar.txt", "is_dir": False, "size": 123}
        Supports legacy single-file reports.
        """
        root = self._root(artifact_id)
        entries: list[dict] = []

        if self.fs.exists(root):
            try:
                for p in self.fs.find(root, withdirs=True):
                    if p == root:
                        continue
                    rel = str(Path(p).relative_to(Path(root)))
                    is_dir = False
                    size = 0
                    try:
                        is_dir = self.fs.isdir(p)
                    except Exception:
                        pass
                    if not is_dir:
                        try:
                            size = self.fs.size(p) or 0
                        except Exception:
                            pass
                    entries.append({"path": rel, "is_dir": is_dir, "size": size})
            except Exception:
                pass
        else:
            legacy = self._legacy_path(artifact_id)
            if legacy.exists():
                entries.append({
                    "path": self.PRIMARY,
                    "is_dir": False,
                    "size": legacy.stat().st_size if legacy.exists() else 0,
                })

        # Sort: dirs first, then alpha
        entries.sort(key=lambda e: (not e["is_dir"], e["path"].lower()))
        return entries

    def get_nested_tree(self, artifact_id: str) -> dict:
        """Return nested tree dict for a nice collapsible file tree UI.

        Structure: {"name": "", "path": "", "is_dir": True, "children": [ ... ]}
        """
        flat = self.list_tree(artifact_id)
        root = {"name": "", "path": "", "is_dir": True, "size": 0, "children": []}

        for entry in flat:
            parts = entry["path"].split("/")
            current = root
            for i, part in enumerate(parts):
                is_last = i == len(parts) - 1
                found = next((c for c in current["children"] if c["name"] == part), None)
                if not found:
                    node = {
                        "name": part,
                        "path": "/".join(parts[: i + 1]),
                        "is_dir": entry["is_dir"] if is_last else True,
                        "size": entry["size"] if is_last and not entry["is_dir"] else 0,
                        "children": [],
                    }
                    current["children"].append(node)
                    found = node
                current = found

        return root