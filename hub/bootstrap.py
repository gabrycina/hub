from __future__ import annotations

import fcntl
import json
import os
import secrets
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import httpx

import hub.paths as paths

HUB_SERVICE_NAME = "hub"
CONFIG_KEYS = (
    "HUB_DATA_DIR",
    "HUB_OWNER",
    "HUB_API_TOKEN",
    "HUB_PUBLIC_URL",
    "HUB_DEV_USER",
)
NOT_CONFIGURED_MSG = (
    "Hub is not configured. Run `uv run hub init --mcp` once, then restart your agent."
)


def _run(
    command: list[str],
    *,
    timeout: float | None = None,
    **kwargs,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            check=False,
            text=True,
            capture_output=True,
            timeout=timeout,
            **kwargs,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(command, returncode=124, stdout="", stderr="timeout")


def detect_owner() -> str:
    if owner := os.environ.get("HUB_OWNER"):
        return owner
    if not shutil.which("tailscale"):
        return "local@dev"

    result = _run(["tailscale", "status", "--json"], timeout=5)
    if result.returncode == 0 and result.stdout.strip():
        try:
            data = json.loads(result.stdout)
            self_user_id = data.get("Self", {}).get("UserID")
            users = data.get("User", {})
            if self_user_id is not None:
                profile = users.get(str(self_user_id)) or users.get(self_user_id)
                if isinstance(profile, dict):
                    login = profile.get("LoginName", "").strip()
                    if login:
                        return login
        except json.JSONDecodeError:
            pass

    # Older tailscale builds
    result = _run(["tailscale", "whoami"], timeout=5)
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return "local@dev"


def detect_public_url() -> str:
    if url := os.environ.get("HUB_PUBLIC_URL"):
        return url.rstrip("/")

    # Default to localhost until Tailscale Serve is actually configured.
    # setup_tailscale_serve() updates HUB_PUBLIC_URL when serve is active.
    from hub.tailscale_serve import is_serve_configured, tailscale_machine_url

    if is_serve_configured():
        machine_url = tailscale_machine_url()
        if machine_url:
            return machine_url

    load_config_env()
    host = os.environ.get("HUB_HOST", "127.0.0.1")
    port = os.environ.get("HUB_PORT", "8080")
    return f"http://{host}:{port}"


def read_config_file() -> dict[str, str]:
    if not paths.CONFIG_ENV.exists():
        return {}

    values: dict[str, str] = {}
    for line in paths.CONFIG_ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def load_config_env() -> None:
    for key, value in read_config_file().items():
        os.environ.setdefault(key, value)


def config_env() -> dict[str, str]:
    load_config_env()
    return dict(os.environ)


def is_initialized() -> bool:
    return paths.TOKEN_FILE.exists() and paths.CONFIG_ENV.exists()


def _write_config_file(values: dict[str, str]) -> None:
    paths.CONFIG_ENV.write_text(
        "\n".join(f"{key}={values[key]}" for key in CONFIG_KEYS if key in values) + "\n",
        encoding="utf-8",
    )
    paths.CONFIG_ENV.chmod(0o600)


def init_config(*, repo_dir: Path | None = None) -> dict[str, str]:
    paths.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    (paths.DATA_DIR / "artifacts").mkdir(parents=True, exist_ok=True)

    if paths.TOKEN_FILE.exists():
        token = paths.TOKEN_FILE.read_text(encoding="utf-8").strip()
    else:
        token = secrets.token_urlsafe(32)
        paths.TOKEN_FILE.write_text(token, encoding="utf-8")
        paths.TOKEN_FILE.chmod(0o600)

    existing = read_config_file()
    defaults = {
        "HUB_DATA_DIR": str(paths.DATA_DIR),
        "HUB_OWNER": detect_owner(),
        "HUB_API_TOKEN": token,
        "HUB_PUBLIC_URL": detect_public_url(),
        "HUB_DEV_USER": detect_owner(),
    }

    merged = dict(existing)
    for key, value in defaults.items():
        merged.setdefault(key, value)

    merged["HUB_API_TOKEN"] = token
    merged["HUB_DATA_DIR"] = str(paths.DATA_DIR)

    if merged.get("HUB_DEV_USER") in (None, "") and merged.get("HUB_OWNER"):
        merged["HUB_DEV_USER"] = merged["HUB_OWNER"]

    _write_config_file(merged)

    for key in CONFIG_KEYS:
        if key in merged:
            os.environ[key] = merged[key]

    return {
        "token": token,
        "owner": merged["HUB_OWNER"],
        "public_url": merged["HUB_PUBLIC_URL"],
        "repo_dir": str(repo_dir or Path.cwd()),
    }


def hub_health_url() -> str:
    load_config_env()
    host = os.environ.get("HUB_HOST", "127.0.0.1")
    port = os.environ.get("HUB_PORT", "8080")
    return f"http://{host}:{port}/health"


def _health_payload(response: httpx.Response) -> dict | None:
    if response.status_code != 200:
        return None
    try:
        payload = response.json()
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def is_hub_running() -> bool:
    try:
        response = httpx.get(hub_health_url(), timeout=1.0)
    except httpx.HTTPError:
        return False

    payload = _health_payload(response)
    if not payload:
        return False
    return (
        payload.get("status") == "ok"
        and payload.get("service") == HUB_SERVICE_NAME
    )


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _tail_log(lines: int = 20) -> str:
    if not paths.LOG_FILE.exists():
        return ""
    content = paths.LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
    if not content:
        return ""
    return "\n".join(content[-lines:])


@contextmanager
def _start_lock():
    paths.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with paths.LOCK_FILE.open("w", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _hub_process_env() -> dict[str, str]:
    env = os.environ.copy()
    load_config_env()
    env.update({k: v for k, v in os.environ.items() if k.startswith("HUB_")})
    return env


def start_hub_background() -> None:
    if is_hub_running():
        return

    with _start_lock():
        if is_hub_running():
            return

        if paths.PID_FILE.exists():
            try:
                pid = int(paths.PID_FILE.read_text(encoding="utf-8").strip())
            except ValueError:
                pid = 0
            if pid and _pid_alive(pid) and is_hub_running():
                return

        paths.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        log_handle = paths.LOG_FILE.open("a", encoding="utf-8")
        env = _hub_process_env()
        process = subprocess.Popen(
            [sys.executable, "-m", "hub.main", "run"],
            env=env,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        paths.PID_FILE.write_text(str(process.pid), encoding="utf-8")

        for _ in range(20):
            if is_hub_running():
                return
            if process.poll() is not None:
                break
            time.sleep(0.25)

        log_tail = _tail_log()
        detail = log_tail or f"Process exited with code {process.returncode}"
        raise RuntimeError(
            "Hub failed to start. Run `uv run hub run` to see errors in the foreground.\n"
            f"Recent log output:\n{detail}"
        )


def ensure_hub_running() -> None:
    load_config_env()
    if not is_initialized():
        raise RuntimeError(NOT_CONFIGURED_MSG)
    if not is_hub_running():
        start_hub_background()


def mcp_config(repo_dir: Path | None = None) -> dict:
    if not is_initialized():
        info = init_config(repo_dir=repo_dir)
    else:
        info = _current_info(repo_dir)
    return {
        "mcpServers": {
            "hub": {
                "command": "uv",
                "args": [
                    "--directory",
                    info["repo_dir"],
                    "run",
                    "python",
                    "-m",
                    "hub_mcp.server",
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
    from hub.tailscale_serve import setup_tailscale_serve

    result = setup_tailscale_serve(wait_seconds=0, open_browser=False)
    if result.state == "needs_enable":
        raise RuntimeError(
            "Tailscale Serve is not enabled. Run `uv run hub serve-setup`."
        )
    if result.state == "error":
        raise RuntimeError(result.message or "tailscale serve failed")
    return result.public_url