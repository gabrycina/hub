# Hub

Self-hosted report inbox for AI coding agents. Publish HTML reports from Claude Code via MCP, browse them on a dashboard, and share with colleagues on your Tailnet.

## Quick start (2 commands)

```bash
cd hub
uv sync && uv run hub init --mcp   # one-time: config + Claude Code MCP
```

Restart Claude Code. That's it — Hub auto-starts when the agent uses MCP.

To expose the dashboard on your tailnet (for sharing links with colleagues):

```bash
uv run hub up
```

## How it works

| Step | Who does it |
|------|-------------|
| One-time setup | `hub init --mcp` writes config to `~/.config/hub/` and registers MCP in Claude Code |
| Start hub | Automatic — MCP starts hub in the background on first use |
| Share on tailnet | `hub up` — starts hub + `tailscale serve` |

No manual env vars in MCP config. No second terminal for day-to-day agent use.

## Claude Code MCP

After `hub init --mcp`, your `~/.claude/.mcp.json` contains:

```json
{
  "mcpServers": {
    "hub": {
      "command": "uv",
      "args": ["--directory", "/path/to/hub", "run", "hub-mcp"]
    }
  }
}
```

## Commands

```bash
hub init [--mcp]   # one-time setup
hub up           # start hub + tailscale serve (for sharing)
hub status       # check if hub is running
```

## What you get

- **MCP integration** — `post_report`, `list_reports`, `set_report_visibility`, `get_report_url`
- **Dashboard** — browse, search, preview, download, toggle visibility
- **Private or shareable** — control who on your tailnet can see each report
- **Tailscale-native security** — bind to `127.0.0.1`, expose via `tailscale serve`

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