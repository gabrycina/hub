from __future__ import annotations

import json
import os
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path

import httpx

import hub.paths as paths


def _run(command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, text=True, capture_output=True, **kwargs)


def detect_owner() -> str:
    if owner := os.environ.get("HUB_OWNER"):
        return owner
    if shutil.which("tailscale"):
        result = _run(["tailscale", "whoami"])
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    return "local@dev"


def detect_public_url() -> str:
    if url := os.environ.get("HUB_PUBLIC_URL"):
        return url.rstrip("/")
    if shutil.which("tailscale"):
        result = _run(["tailscale", "status", "--json"])
        if result.returncode == 0 and result.stdout.strip():
            try:
                data = json.loads(result.stdout)
                dns = data.get("Self", {}).get("DNSName", "").rstrip(".")
                if dns:
                    return f"https://{dns}"
            except json.JSONDecodeError:
                pass
    return "http://127.0.0.1:8080"


def load_config_env() -> None:
    if paths.CONFIG_ENV.exists():
        for line in paths.CONFIG_ENV.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key, value)


def config_env() -> dict[str, str]:
    load_config_env()
    return dict(os.environ)


def is_initialized() -> bool:
    return paths.TOKEN_FILE.exists() and paths.CONFIG_ENV.exists()


def init_config(*, repo_dir: Path | None = None) -> dict[str, str]:
    paths.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    (paths.DATA_DIR / "artifacts").mkdir(parents=True, exist_ok=True)

    if paths.TOKEN_FILE.exists():
        token = paths.TOKEN_FILE.read_text(encoding="utf-8").strip()
    else:
        token = secrets.token_urlsafe(32)
        paths.TOKEN_FILE.write_text(token, encoding="utf-8")
        paths.TOKEN_FILE.chmod(0o600)

    owner = detect_owner()
    public_url = detect_public_url()

    paths.CONFIG_ENV.write_text(
        "\n".join(
            [
                f"HUB_DATA_DIR={paths.DATA_DIR}",
                f"HUB_OWNER={owner}",
                f"HUB_API_TOKEN={token}",
                f"HUB_PUBLIC_URL={public_url}",
                f"HUB_DEV_USER={owner}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    paths.CONFIG_ENV.chmod(0o600)

    for key, value in {
        "HUB_DATA_DIR": str(paths.DATA_DIR),
        "HUB_OWNER": owner,
        "HUB_API_TOKEN": token,
        "HUB_PUBLIC_URL": public_url,
        "HUB_DEV_USER": owner,
    }.items():
        os.environ[key] = value

    return {
        "token": token,
        "owner": owner,
        "public_url": public_url,
        "repo_dir": str(repo_dir or Path.cwd()),
    }


def hub_health_url() -> str:
    load_config_env()
    host = os.environ.get("HUB_HOST", "127.0.0.1")
    port = os.environ.get("HUB_PORT", "8080")
    return f"http://{host}:{port}/health"


def is_hub_running() -> bool:
    try:
        response = httpx.get(hub_health_url(), timeout=1.0)
        return response.status_code == 200
    except httpx.HTTPError:
        return False


def _hub_process_env() -> dict[str, str]:
    env = os.environ.copy()
    load_config_env()
    env.update({k: v for k, v in os.environ.items() if k.startswith("HUB_")})
    return env


def start_hub_background() -> None:
    if is_hub_running():
        return

    env = _hub_process_env()
    process = subprocess.Popen(
        [sys.executable, "-m", "hub.main", "run"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    paths.PID_FILE.write_text(str(process.pid), encoding="utf-8")

    for _ in range(20):
        if is_hub_running():
            return
        time.sleep(0.25)

    raise RuntimeError("Hub failed to start. Run `hub up` manually to see errors.")


def ensure_hub_running() -> None:
    load_config_env()
    if not is_initialized():
        init_config()
    if not is_hub_running():
        start_hub_background()


def mcp_config(repo_dir: Path | None = None) -> dict:
    info = init_config(repo_dir=repo_dir) if not is_initialized() else _current_info(repo_dir)
    return {
        "mcpServers": {
            "hub": {
                "command": "uv",
                "args": [
                    "--directory",
                    info["repo_dir"],
                    "run",
                    "hub-mcp",
                ],
            }
        }
    }


def _current_info(repo_dir: Path | None = None) -> dict[str, str]:
    load_config_env()
    return {
        "token": paths.TOKEN_FILE.read_text(encoding="utf-8").strip(),
        "owner": os.environ.get("HUB_OWNER", "local@dev"),
        "public_url": os.environ.get("HUB_PUBLIC_URL", "http://127.0.0.1:8080"),
        "repo_dir": str(repo_dir or Path.cwd()),
    }


def write_claude_mcp_config(repo_dir: Path | None = None) -> Path:
    config = mcp_config(repo_dir=repo_dir)
    paths.CLAUDE_MCP.parent.mkdir(parents=True, exist_ok=True)

    if paths.CLAUDE_MCP.exists():
        existing = json.loads(paths.CLAUDE_MCP.read_text(encoding="utf-8") or "{}")
        servers = existing.setdefault("mcpServers", {})
        servers.update(config["mcpServers"])
        paths.CLAUDE_MCP.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    else:
        paths.CLAUDE_MCP.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    return paths.CLAUDE_MCP


def start_tailscale_serve() -> str | None:
    if not shutil.which("tailscale"):
        return None

    load_config_env()
    port = os.environ.get("HUB_PORT", "8080")
    result = _run(["tailscale", "serve", "--bg", port])
    if result.returncode != 0:
        result = _run(["tailscale", "serve", port])
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "tailscale serve failed")
    return detect_public_url()