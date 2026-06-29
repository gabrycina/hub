from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass

import hub.paths as paths
from hub.bootstrap import _run, load_config_env, read_config_file
from hub.constants import DEFAULT_PORT

ENABLE_URL_RE = re.compile(r"https://login\.tailscale\.com/f/serve\?node=\S+")


@dataclass
class ServeSetupResult:
    state: str  # active | needs_enable | local_only | error
    public_url: str
    enable_url: str | None = None
    message: str = ""


def _tailscale_self() -> dict | None:
    if not shutil.which("tailscale"):
        return None

    result = _run(["tailscale", "status", "--json"], timeout=5)
    if result.returncode != 0 or not result.stdout.strip():
        return None

    try:
        import json

        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None

    self = data.get("Self")
    return self if isinstance(self, dict) else None


def tailscale_machine_url() -> str | None:
    self = _tailscale_self()
    if not self:
        return None

    dns = self.get("DNSName", "").rstrip(".")
    if not dns:
        return None
    return f"https://{dns}"


def tailscale_enable_url() -> str | None:
    """Build the one-time Serve approval URL from this machine's tailnet node ID."""
    self = _tailscale_self()
    if not self:
        return None

    node_id = self.get("ID", "").strip()
    if not node_id:
        return None
    return f"https://login.tailscale.com/f/serve?node={node_id}"


def parse_enable_url(output: str) -> str | None:
    match = ENABLE_URL_RE.search(output)
    return match.group(0) if match else None


def resolve_enable_url(output: str = "") -> str | None:
    return parse_enable_url(output) or tailscale_enable_url()


def serve_status_output() -> str:
    if not shutil.which("tailscale"):
        return ""
    result = _run(["tailscale", "serve", "status"], timeout=5)
    return (result.stdout + result.stderr).strip()


def is_serve_configured() -> bool:
    output = serve_status_output().lower()
    if not output:
        return False
    if "no serve config" in output:
        return False
    if "not enabled" in output:
        return False
    return True


def _local_public_url() -> str:
    load_config_env()
    host = os.environ.get("HUB_HOST", "127.0.0.1")
    port = os.environ.get("HUB_PORT", str(DEFAULT_PORT))
    return f"http://{host}:{port}"


def update_public_url(public_url: str) -> None:
    values = read_config_file()
    values["HUB_PUBLIC_URL"] = public_url.rstrip("/")
    paths.CONFIG_ENV.parent.mkdir(parents=True, exist_ok=True)
    from hub.bootstrap import CONFIG_KEYS, _write_config_file

    for key in CONFIG_KEYS:
        values.setdefault(key, os.environ.get(key, ""))
    _write_config_file({k: v for k, v in values.items() if v})
    os.environ["HUB_PUBLIC_URL"] = values["HUB_PUBLIC_URL"]


def _try_open_enable_url(enable_url: str) -> None:
    if sys.platform == "darwin":
        subprocess.run(["open", enable_url], check=False)
    elif sys.platform.startswith("linux") and shutil.which("xdg-open"):
        subprocess.run(["xdg-open", enable_url], check=False)


def _attempt_serve(port: str, *, timeout: float = 5.0) -> subprocess.CompletedProcess[str]:
    # Never run foreground `tailscale serve` — it blocks until interrupted.
    return _run(["tailscale", "serve", "--bg", port], timeout=timeout)


def _serve_output_needs_enable(output: str) -> bool:
    return "serve is not enabled" in output.lower() or "not enabled on your tailnet" in output.lower()


def setup_tailscale_serve(
    *,
    wait_seconds: int = 90,
    open_browser: bool = True,
) -> ServeSetupResult:
    load_config_env()
    port = os.environ.get("HUB_PORT", str(DEFAULT_PORT))

    if not shutil.which("tailscale"):
        local = _local_public_url()
        update_public_url(local)
        return ServeSetupResult(
            state="local_only",
            public_url=local,
            message="Tailscale not installed. Hub is local-only.",
        )

    if is_serve_configured():
        public = tailscale_machine_url() or _local_public_url()
        update_public_url(public)
        return ServeSetupResult(
            state="active",
            public_url=public,
            message="Tailscale Serve is already configured.",
        )

    result = _attempt_serve(port)
    combined = f"{result.stdout}\n{result.stderr}"

    if not _serve_output_needs_enable(combined) and result.returncode == 0:
        public = tailscale_machine_url() or _local_public_url()
        update_public_url(public)
        return ServeSetupResult(
            state="active",
            public_url=public,
            message="Tailscale Serve configured.",
        )

    enable_url = resolve_enable_url(combined)
    if enable_url and open_browser:
        _try_open_enable_url(enable_url)

    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        time.sleep(2)
        if is_serve_configured():
            public = tailscale_machine_url() or _local_public_url()
            update_public_url(public)
            return ServeSetupResult(
                state="active",
                public_url=public,
                message="Tailscale Serve enabled and configured.",
            )
        retry = _attempt_serve(port)
        retry_output = f"{retry.stdout}\n{retry.stderr}"
        if not _serve_output_needs_enable(retry_output) and retry.returncode == 0:
            public = tailscale_machine_url() or _local_public_url()
            update_public_url(public)
            return ServeSetupResult(
                state="active",
                public_url=public,
                message="Tailscale Serve configured.",
            )
        enable_url = enable_url or resolve_enable_url(retry_output)

    local = _local_public_url()
    update_public_url(local)
    return ServeSetupResult(
        state="needs_enable",
        public_url=local,
        enable_url=enable_url,
        message=(
            "Tailscale Serve is not enabled on your tailnet yet. "
            "Hub works locally, but .ts.net links will not work until Serve is enabled."
        ),
    )


def current_serve_state() -> ServeSetupResult:
    if not shutil.which("tailscale"):
        local = _local_public_url()
        return ServeSetupResult(state="local_only", public_url=local)

    if is_serve_configured():
        public = tailscale_machine_url() or _local_public_url()
        return ServeSetupResult(state="active", public_url=public)

    load_config_env()
    public = os.environ.get("HUB_PUBLIC_URL", _local_public_url())
    return ServeSetupResult(
        state="needs_enable",
        public_url=public,
        enable_url=tailscale_enable_url(),
        message="Tailscale Serve is not configured. Run `uv run hub serve-setup`.",
    )