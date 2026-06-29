from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from hub.bootstrap import (
    ensure_hub_running,
    init_config,
    is_hub_running,
    is_initialized,
    load_config_env,
    mcp_config,
    set_config_values,
)
from hub.constants import DEFAULT_HOST, DEFAULT_PORT
from hub.mcp_agents import agent_restart_message, configure_mcp_agents, manual_mcp_snippet
from hub.tailscale_serve import current_serve_state, setup_tailscale_serve


def _local_url() -> str:
    import os

    load_config_env()
    host = os.environ.get("HUB_HOST", DEFAULT_HOST)
    port = os.environ.get("HUB_PORT", str(DEFAULT_PORT))
    return f"http://{host}:{port}"


def _port() -> str:
    import os

    load_config_env()
    return os.environ.get("HUB_PORT", str(DEFAULT_PORT))


def _detect_server_url() -> str:
    """Best-effort base URL others use to reach this server: the primary outbound IP."""
    import socket

    ip = "127.0.0.1"
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # No packets are sent; this just picks the interface for the default route.
        sock.connect(("10.255.255.255", 1))
        ip = sock.getsockname()[0]
        sock.close()
    except OSError:
        pass
    return f"http://{ip}:{_port()}"


def _print_serve_result(result, *, interactive: bool) -> int:
    if result.state == "active":
        print(f"  Tailnet:  {result.public_url}")
        if result.message:
            print(f"  Serve:    {result.message}")
        return 0

    if result.state == "local_only":
        print(f"  Mode:     local only ({result.public_url})")
        if result.message:
            print(f"  Note:     {result.message}")
        return 0

    print(f"  Mode:     local only ({result.public_url})")
    print(f"  Serve:    {result.message}")
    if result.state == "needs_enable":
        print("\nEnable Tailscale Serve (one-time, required for .ts.net links):")
        if result.enable_url:
            print(f"  {result.enable_url}")
            if interactive:
                print("\nWe tried to open that link in your browser.")
        else:
            print(f"  Open the enable link from: tailscale serve --bg {DEFAULT_PORT}")
        if interactive:
            print("After approving, run:")
            print("  uv run hub serve-setup")
    return 2 if result.state == "needs_enable" else 1


def cmd_init(args: argparse.Namespace) -> int:
    info = init_config(repo_dir=Path(args.repo).resolve())

    print("Hub initialized.")
    print(f"  Config: ~/.config/hub/config.env")
    print(f"  Owner:  {info['owner']}")

    if args.mcp:
        repo = Path(args.repo).resolve()
        agents = configure_mcp_agents(repo_dir=repo)
        print()
        for name, path in agents:
            print(f"MCP config written for {name}: {path}")
        print(agent_restart_message(agents))
        print()
        print(manual_mcp_snippet(repo_dir=repo))
    else:
        print("\nMCP config (add to your agent):")
        print(json.dumps(mcp_config(repo_dir=Path(args.repo).resolve()), indent=2))

    if args.server:
        public_url = args.public_url.rstrip("/") or _detect_server_url()
        values = {
            "HUB_HOST": "0.0.0.0",
            "HUB_TRUST_NETWORK": "true",
            "HUB_PUBLIC_URL": public_url,
        }
        if args.site_name:
            values["HUB_SITE_NAME"] = args.site_name
        set_config_values(values)
        print("\nServer mode configured (no Tailscale Serve).")
        print(f"  Binding:  0.0.0.0:{_port()}")
        print(f"  Public:   {public_url}")
        if args.site_name:
            print(f"  Branding: {args.site_name} Hub")
        print("  Viewing:  anyone who can reach this server can view shareable reports;")
        print("            publishing still requires the API token.")
        print("\nStart it with: uv run hub up --no-serve")
        return 0

    if args.no_serve:
        print("\nSkipped Tailscale Serve (--no-serve).")
        print(f"  Local: {_local_url()}")
        return 0

    print("\nSetting up Tailscale Serve...")
    ensure_hub_running()
    result = setup_tailscale_serve(
        wait_seconds=args.serve_wait,
        open_browser=not args.no_open,
    )
    print("Hub is running.")
    print(f"  Local:    {_local_url()}")
    return _print_serve_result(result, interactive=True)


def cmd_up(args: argparse.Namespace) -> int:
    if not is_initialized():
        init_config(repo_dir=Path(args.repo).resolve())

    ensure_hub_running()

    print("Hub is running.")
    print(f"  Local:    {_local_url()}")

    if args.no_serve:
        print("  Mode:     local only (--no-serve)")
        return 0

    result = setup_tailscale_serve(
        wait_seconds=args.serve_wait,
        open_browser=not args.no_open,
    )
    return _print_serve_result(result, interactive=True)


def cmd_serve_setup(args: argparse.Namespace) -> int:
    if not is_initialized():
        print("Run `uv run hub init --mcp` first.", file=sys.stderr)
        return 1

    ensure_hub_running()
    print("Configuring Tailscale Serve...")
    result = setup_tailscale_serve(
        wait_seconds=args.serve_wait,
        open_browser=not args.no_open,
    )
    print(f"  Local:    {_local_url()}")
    return _print_serve_result(result, interactive=True)


def cmd_status(_: argparse.Namespace) -> int:
    initialized = is_initialized()
    running = is_hub_running() if initialized else False
    print(f"initialized: {initialized}")
    print(f"running:     {running}")

    if not initialized:
        return 0

    serve = current_serve_state()
    print(f"serve:       {serve.state}")
    print(f"public_url:  {serve.public_url}")
    if serve.enable_url:
        print(f"enable_url:  {serve.enable_url}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hub", description="Self-hosted report inbox")
    parser.add_argument(
        "--repo",
        default=".",
        help="Path to the hub repo (for MCP config generation)",
    )
    sub = parser.add_subparsers(dest="command")

    init_parser = sub.add_parser("init", help="One-time setup")
    init_parser.add_argument(
        "--mcp",
        action="store_true",
        help="Register the Hub MCP server with detected agents (Claude Code, Cursor, Codex, Grok)",
    )
    init_parser.add_argument(
        "--no-serve",
        action="store_true",
        help="Skip Tailscale Serve setup (local only)",
    )
    init_parser.add_argument(
        "--server",
        action="store_true",
        help=(
            "Host on a server/devbox instead of locally over Tailscale Serve: "
            "bind to 0.0.0.0 and trust the network for viewing (anyone who can reach "
            "the server sees shareable reports). Publishing still requires the API token."
        ),
    )
    init_parser.add_argument(
        "--site-name",
        default="",
        help="Branding shown in the dashboard title, e.g. 'Gen AI' renders as 'Gen AI Hub'",
    )
    init_parser.add_argument(
        "--public-url",
        default="",
        help="Base URL others use to reach this server (e.g. http://172.31.95.176:17482). "
        "Defaults to the detected host IP in --server mode",
    )
    init_parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open the Tailscale Serve enable URL in a browser",
    )
    init_parser.add_argument(
        "--serve-wait",
        type=int,
        default=90,
        help="Seconds to wait for Tailscale Serve approval (default: 90)",
    )

    up_parser = sub.add_parser("up", help="Start hub and expose on tailnet")
    up_parser.add_argument(
        "--no-serve",
        action="store_true",
        help="Start hub locally without tailscale serve",
    )
    up_parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open the Tailscale Serve enable URL in a browser",
    )
    up_parser.add_argument(
        "--serve-wait",
        type=int,
        default=90,
        help="Seconds to wait for Tailscale Serve approval (default: 90)",
    )

    serve_parser = sub.add_parser(
        "serve-setup",
        help="Enable and configure Tailscale Serve for Hub",
    )
    serve_parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open the Tailscale Serve enable URL in a browser",
    )
    serve_parser.add_argument(
        "--serve-wait",
        type=int,
        default=90,
        help="Seconds to wait for Tailscale Serve approval (default: 90)",
    )

    sub.add_parser("status", help="Show hub status")
    sub.add_parser("run", help=argparse.SUPPRESS)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        return cmd_init(args)
    if args.command == "up":
        return cmd_up(args)
    if args.command == "serve-setup":
        return cmd_serve_setup(args)
    if args.command == "status":
        return cmd_status(args)
    if args.command == "run":
        from hub.main import run_server

        run_server()
        return 0

    parser.print_help()
    return 1