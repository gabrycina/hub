from __future__ import annotations

import json
import shutil
from pathlib import Path

import hub.paths as paths
from hub.bootstrap import _run, mcp_config

HUB_SERVER_NAME = "hub"


def _stdio_command(repo_dir: Path) -> list[str]:
    server = mcp_config(repo_dir)["mcpServers"][HUB_SERVER_NAME]
    return [server["command"], *server["args"]]


def _write_json_mcp_config(path: Path, repo_dir: Path) -> None:
    config = mcp_config(repo_dir)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8") or "{}")
        servers = existing.setdefault("mcpServers", {})
        servers.update(config["mcpServers"])
        path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    else:
        path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def _register_json_agent(name: str, path: Path, repo_dir: Path) -> tuple[str, str] | None:
    _write_json_mcp_config(path, repo_dir)
    return name, str(path)


def _resolve_cli(command: str, fallbacks: tuple[str, ...] = ()) -> str | None:
    if resolved := shutil.which(command):
        return resolved
    for candidate in fallbacks:
        if Path(candidate).is_file():
            return candidate
    return None


def _register_cli_agent(
    name: str,
    cli: str,
    config_path: Path,
    repo_dir: Path,
    *,
    fallbacks: tuple[str, ...] = (),
    extra_args: tuple[str, ...] = (),
) -> tuple[str, str] | None:
    resolved = _resolve_cli(cli, fallbacks)
    if not resolved:
        return None

    command = _stdio_command(repo_dir)
    # Best-effort remove first so re-running `init --mcp` is idempotent
    # (the add subcommand errors when the server name already exists).
    _run([resolved, "mcp", "remove", HUB_SERVER_NAME, *extra_args], timeout=30)
    result = _run(
        [resolved, "mcp", "add", HUB_SERVER_NAME, *extra_args, "--", *command],
        timeout=30,
    )
    if result.returncode != 0:
        return None
    return name, str(config_path)


def configure_mcp_agents(repo_dir: Path | None = None) -> list[tuple[str, str]]:
    """Register Hub MCP with every detected agent host on this machine."""
    repo = Path(repo_dir or Path.cwd()).resolve()
    configured: list[tuple[str, str]] = []

    json_targets = (("Cursor", paths.CURSOR_MCP),)
    for name, path in json_targets:
        configured.append(_register_json_agent(name, path, repo))

    # Claude Code, Grok, and Codex own their own config files; register through
    # their CLIs so the server lands where each agent actually reads it. Claude
    # Code is registered at user scope so Hub is available across all projects.
    cli_targets = (
        ("Claude Code", "claude", paths.CLAUDE_CONFIG, (), ("--scope", "user")),
        ("Grok Build", "grok", paths.GROK_CONFIG, (), ()),
        (
            "Codex",
            "codex",
            paths.CODEX_CONFIG,
            ("/Applications/Codex.app/Contents/Resources/codex",),
            (),
        ),
    )
    for name, cli, path, fallbacks, extra_args in cli_targets:
        entry = _register_cli_agent(
            name, cli, path, repo, fallbacks=fallbacks, extra_args=extra_args
        )
        if entry:
            configured.append(entry)

    return configured


def agent_restart_message(agents: list[tuple[str, str]]) -> str:
    names = [name for name, _ in agents]
    if not names:
        return "Restart your agent to load the Hub MCP server."
    if len(names) == 1:
        return f"Restart {names[0]} to load the Hub MCP server."
    if len(names) == 2:
        return f"Restart {names[0]} and {names[1]} to load the Hub MCP server."
    return f"Restart {', '.join(names[:-1])}, and {names[-1]} to load the Hub MCP server."


def manual_mcp_snippet(repo_dir: Path | None = None) -> str:
    repo = Path(repo_dir or Path.cwd()).resolve()
    server = mcp_config(repo)["mcpServers"][HUB_SERVER_NAME]
    lines = [
        "Other MCP clients (paste into their config):",
        f"  command: {server['command']}",
        f"  args: {json.dumps(server['args'])}",
    ]
    return "\n".join(lines)