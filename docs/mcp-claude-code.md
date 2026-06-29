# Claude Code MCP setup

## One command

```bash
uv sync && uv run hub init --mcp
```

This will:

1. Create `~/.config/hub/` (token, config, data dir)
2. Detect your Tailscale identity and machine URL
3. Write the MCP entry to `~/.claude/.mcp.json`

Restart Claude Code. Hub starts automatically when the agent first calls an MCP tool.

## Sharing reports on your tailnet

MCP works with localhost only. For colleagues to open your dashboard and shareable links:

```bash
uv run hub up
```

## MCP tools

| Tool | Description |
|------|-------------|
| `post_report` | Publish HTML with title and visibility |
| `list_reports` | List reports by scope (`mine`, `shared`, `all`) |
| `set_report_visibility` | Toggle `private` / `shareable` |
| `get_report_url` | Get URL for an existing report |

## Skill

Use the bundled `skills/hub-publish` skill so the agent generates consistent HTML before publishing.