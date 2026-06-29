# Hub

Self-hosted report inbox for AI coding agents. Publish HTML reports from Claude Code via MCP, browse them on a dashboard, and share with colleagues on your Tailnet.

## Quick start

```bash
cd hub
uv sync
./scripts/setup.sh

# Terminal 1 — run hub (localhost only)
set -a && source ~/.config/hub/config.env && set +a && uv run hub

# Terminal 2 — expose on tailnet
./scripts/tailscale-serve.sh
```

Add the MCP config printed by `setup.sh` to Claude Code, then ask your agent to publish a report with the `hub-publish` skill.

## What you get

- **MCP integration** — `post_report`, `list_reports`, `set_report_visibility`, `get_report_url`
- **Dashboard** — browse, search, preview, download, toggle visibility
- **Private or shareable** — control who on your tailnet can see each report
- **Tailscale-native security** — bind to `127.0.0.1`, expose via `tailscale serve`, identity via `Tailscale-User-Login`

## Claude Code MCP

```json
{
  "mcpServers": {
    "hub": {
      "command": "uv",
      "args": ["--directory", "/path/to/hub", "run", "hub-mcp"],
      "env": {
        "HUB_URL": "http://127.0.0.1:8080",
        "HUB_API_TOKEN": "<from ~/.config/hub/token>",
        "HUB_PUBLIC_URL": "https://your-machine.your-tailnet.ts.net"
      }
    }
  }
}
```

## Docs

- [Tailscale setup](docs/tailscale.md)
- [Claude Code MCP setup](docs/mcp-claude-code.md)
- [Security model](docs/security.md)

## Development

```bash
uv sync --extra dev
uv run pytest
```

## License

MIT