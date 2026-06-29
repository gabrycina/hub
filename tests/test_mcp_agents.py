import subprocess
from pathlib import Path
from unittest.mock import patch

from hub import mcp_agents


def _ok(*_args, **_kwargs):
    return subprocess.CompletedProcess([], returncode=0, stdout="", stderr="")


@patch("hub.mcp_agents.mcp_config")
def test_claude_registered_via_cli_at_user_scope(mock_mcp_config, tmp_path: Path):
    mock_mcp_config.return_value = {
        "mcpServers": {
            "hub": {"command": "uv", "args": ["--directory", "/repo", "run", "x"]}
        }
    }
    calls: list[list[str]] = []

    def fake_run(command, **_kwargs):
        calls.append(command)
        return _ok()

    # Only the `claude` CLI resolves; Grok/Codex are absent.
    def fake_resolve(command, fallbacks=()):
        return "/usr/bin/claude" if command == "claude" else None

    with (
        patch("hub.mcp_agents._run", side_effect=fake_run),
        patch("hub.mcp_agents._resolve_cli", side_effect=fake_resolve),
        patch("hub.mcp_agents._write_json_mcp_config"),
    ):
        configured = mcp_agents.configure_mcp_agents(repo_dir=tmp_path)

    names = [name for name, _ in configured]
    assert "Claude Code" in names

    add_calls = [c for c in calls if c[:3] == ["/usr/bin/claude", "mcp", "add"]]
    assert len(add_calls) == 1
    add = add_calls[0]
    # User scope so Hub is available across all projects, and the server
    # command follows the `--` separator.
    assert "--scope" in add and add[add.index("--scope") + 1] == "user"
    assert "--" in add
    assert add[add.index("--") + 1 :] == ["uv", "--directory", "/repo", "run", "x"]

    # Idempotent: a remove is attempted before add.
    assert ["/usr/bin/claude", "mcp", "remove", "hub", "--scope", "user"] in calls


@patch("hub.mcp_agents.mcp_config")
def test_no_claude_cli_skips_claude(mock_mcp_config, tmp_path: Path):
    mock_mcp_config.return_value = {
        "mcpServers": {"hub": {"command": "uv", "args": ["x"]}}
    }
    with (
        patch("hub.mcp_agents._run", side_effect=_ok),
        patch("hub.mcp_agents._resolve_cli", return_value=None),
        patch("hub.mcp_agents._write_json_mcp_config"),
    ):
        configured = mcp_agents.configure_mcp_agents(repo_dir=tmp_path)

    assert "Claude Code" not in [name for name, _ in configured]
