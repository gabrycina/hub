import json
from pathlib import Path

import pytest

from hub.bootstrap import (
    NOT_CONFIGURED_MSG,
    ensure_hub_running,
    init_config,
    is_hub_running,
    mcp_config,
    read_config_file,
)


def _patch_paths(monkeypatch, tmp_path: Path, config_dir: Path):
    monkeypatch.setenv("HOME", str(tmp_path))

    import hub.paths as paths

    monkeypatch.setattr(paths, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(paths, "CONFIG_ENV", config_dir / "config.env")
    monkeypatch.setattr(paths, "TOKEN_FILE", config_dir / "token")
    monkeypatch.setattr(paths, "DATA_DIR", config_dir / "data")
    monkeypatch.setattr(paths, "PID_FILE", config_dir / "hub.pid")
    monkeypatch.setattr(paths, "LOCK_FILE", config_dir / "hub.lock")
    monkeypatch.setattr(paths, "LOG_FILE", config_dir / "hub.log")


def test_init_config_creates_files(tmp_path: Path, monkeypatch):
    config_dir = tmp_path / "config"
    _patch_paths(monkeypatch, tmp_path, config_dir)

    info = init_config(repo_dir=tmp_path / "repo")

    assert (config_dir / "token").exists()
    assert (config_dir / "config.env").exists()
    assert info["owner"]
    assert info["public_url"]


def test_init_config_preserves_existing_values(tmp_path: Path, monkeypatch):
    config_dir = tmp_path / "config"
    _patch_paths(monkeypatch, tmp_path, config_dir)

    init_config(repo_dir=tmp_path / "repo")
    config_dir.joinpath("config.env").write_text(
        "\n".join(
            [
                f"HUB_DATA_DIR={config_dir / 'data'}",
                "HUB_OWNER=custom@example.com",
                f"HUB_API_TOKEN={config_dir.joinpath('token').read_text().strip()}",
                "HUB_PUBLIC_URL=https://custom.tailnet.ts.net",
                "HUB_DEV_USER=custom@example.com",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("HUB_OWNER", "spoofed@example.com")
    monkeypatch.setenv("HUB_PUBLIC_URL", "https://wrong.example.com")

    info = init_config(repo_dir=tmp_path / "repo")
    saved = read_config_file()

    assert info["owner"] == "custom@example.com"
    assert info["public_url"] == "https://custom.tailnet.ts.net"
    assert saved["HUB_OWNER"] == "custom@example.com"
    assert saved["HUB_PUBLIC_URL"] == "https://custom.tailnet.ts.net"


def test_mcp_config_has_no_env_vars(tmp_path: Path, monkeypatch):
    config_dir = tmp_path / "config"
    _patch_paths(monkeypatch, tmp_path, config_dir)

    init_config(repo_dir=tmp_path / "repo")
    config = mcp_config(repo_dir=tmp_path / "repo")

    server = config["mcpServers"]["hub"]
    assert "env" not in server
    assert server["args"][-1] == "hub_mcp.server"


def test_ensure_hub_running_requires_init(tmp_path: Path, monkeypatch):
    config_dir = tmp_path / "config"
    _patch_paths(monkeypatch, tmp_path, config_dir)

    with pytest.raises(RuntimeError, match=NOT_CONFIGURED_MSG):
        ensure_hub_running()


def test_is_hub_running_rejects_non_hub_health(monkeypatch):
    import httpx

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"status": "ok"}

    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: FakeResponse())
    assert is_hub_running() is False