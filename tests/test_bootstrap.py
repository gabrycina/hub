import json
from pathlib import Path

from hub.bootstrap import init_config, is_initialized, mcp_config


def test_init_config_creates_files(tmp_path: Path, monkeypatch):
    config_dir = tmp_path / "config"
    monkeypatch.setenv("HOME", str(tmp_path))

    import hub.paths as paths

    monkeypatch.setattr(paths, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(paths, "CONFIG_ENV", config_dir / "config.env")
    monkeypatch.setattr(paths, "TOKEN_FILE", config_dir / "token")
    monkeypatch.setattr(paths, "DATA_DIR", config_dir / "data")

    info = init_config(repo_dir=tmp_path / "repo")

    assert (config_dir / "token").exists()
    assert (config_dir / "config.env").exists()
    assert info["owner"]
    assert info["public_url"]


def test_mcp_config_has_no_env_vars(tmp_path: Path, monkeypatch):
    config_dir = tmp_path / "config"
    monkeypatch.setenv("HOME", str(tmp_path))

    import hub.paths as paths

    monkeypatch.setattr(paths, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(paths, "CONFIG_ENV", config_dir / "config.env")
    monkeypatch.setattr(paths, "TOKEN_FILE", config_dir / "token")
    monkeypatch.setattr(paths, "DATA_DIR", config_dir / "data")

    init_config(repo_dir=tmp_path / "repo")
    config = mcp_config(repo_dir=tmp_path / "repo")

    server = config["mcpServers"]["hub"]
    assert "env" not in server
    assert server["args"][-1] == "hub-mcp"