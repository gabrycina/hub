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
    mcp_config,
    write_claude_mcp_config,
)
from hub.tailscale_serve import current_serve_state, setup_tailscale_serve


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
    if result.enable_url:
        print("\nEnable Tailscale Serve (one-time, required for .ts.net links):")
        print(f"  {result.enable_url}")
        if interactive:
            print("\nWe tried to open that link in your browser.")
            print("After approving, run:")
            print("  uv run hub serve-setup")
    return 2 if result.state == "needs_enable" else 1


def cmd_init(args: argparse.Namespace) -> int:
    info = init_config(repo_dir=Path(args.repo).resolve())

    print("Hub initialized.")
    print(f"  Config: ~/.config/hub/config.env")
    print(f"  Owner:  {info['owner']}")

    if args.mcp:
        path = write_claude_mcp_config(repo_dir=Path(args.repo).resolve())
        print(f"\nMCP config written to {path}")
        print("Restart Claude Code to load the Hub MCP server.")
    else:
        print("\nMCP config (add to Claude Code):")
        print(json.dumps(mcp_config(repo_dir=Path(args.repo).resolve()), indent=2))

    if args.no_serve:
        print("\nSkipped Tailscale Serve (--no-serve).")
        print(f"  Local: http://127.0.0.1:8080")
        return 0

    print("\nSetting up Tailscale Serve...")
    ensure_hub_running()
    result = setup_tailscale_serve(
        wait_seconds=args.serve_wait,
        open_browser=not args.no_open,
    )
    print("Hub is running.")
    print(f"  Local:    http://127.0.0.1:8080")
    return _print_serve_result(result, interactive=True)


def cmd_up(args: argparse.Namespace) -> int:
    if not is_initialized():
        init_config(repo_dir=Path(args.repo).resolve())

    ensure_hub_running()

    print("Hub is running.")
    print(f"  Local:    http://127.0.0.1:8080")

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
    print(f"  Local:    http://127.0.0.1:8080")
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
        help="Write MCP config to ~/.claude/.mcp.json",
    )
    init_parser.add_argument(
        "--no-serve",
        action="store_true",
        help="Skip Tailscale Serve setup (local only)",
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