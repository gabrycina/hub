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
    start_tailscale_serve,
    write_claude_mcp_config,
)


def cmd_init(args: argparse.Namespace) -> int:
    info = init_config(repo_dir=Path(args.repo).resolve())

    print("Hub initialized.")
    print(f"  Config: ~/.config/hub/config.env")
    print(f"  Owner:  {info['owner']}")
    print(f"  URL:    {info['public_url']}")

    if args.mcp:
        path = write_claude_mcp_config(repo_dir=Path(args.repo).resolve())
        print(f"\nMCP config written to {path}")
        print("Restart Claude Code to load the Hub MCP server.")
    else:
        print("\nMCP config (add to Claude Code):")
        print(json.dumps(mcp_config(repo_dir=Path(args.repo).resolve()), indent=2))

    return 0


def cmd_up(args: argparse.Namespace) -> int:
    if not is_initialized():
        init_config(repo_dir=Path(args.repo).resolve())

    ensure_hub_running()
    public_url = None

    if not args.no_serve:
        try:
            public_url = start_tailscale_serve()
        except RuntimeError as exc:
            print(f"Warning: {exc}", file=sys.stderr)
            print("Hub is running locally. Install Tailscale to share on your tailnet.")

    print("Hub is running.")
    print(f"  Local:    http://127.0.0.1:8080")
    if public_url:
        print(f"  Tailnet:  {public_url}")
    print("\nLeave this machine awake, or run `hub up` again later.")
    return 0


def cmd_status(_: argparse.Namespace) -> int:
    initialized = is_initialized()
    running = is_hub_running() if initialized else False
    print(f"initialized: {initialized}")
    print(f"running:     {running}")
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

    up_parser = sub.add_parser("up", help="Start hub and expose on tailnet")
    up_parser.add_argument(
        "--no-serve",
        action="store_true",
        help="Start hub locally without tailscale serve",
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
    if args.command == "status":
        return cmd_status(args)
    if args.command == "run":
        from hub.main import run_server

        run_server()
        return 0

    parser.print_help()
    return 1