# Claude Code MCP setup

## 1. Initialize Hub

```bash
./scripts/setup.sh
```

This creates:

- `~/.config/hub/token` — API token for MCP
- `~/.config/hub/config.env` — environment variables
- MCP config snippet for Claude Code

## 2. Run Hub

```bash
set -a && source ~/.config/hub/config.env && set +a
uv run hub
```

## 3. Add MCP server

Paste the JSON from `setup.sh` into your Claude Code MCP config.

## 4. Use the skill

Copy `skills/hub-publish/` to your project's `.claude/skills/` or reference it from this repo.

Example prompt:

> Generate an HTML report explaining our API migration plan and publish it to Hub as shareable.

The agent will call `post_report` and return your Tailscale URL.

## MCP tools

| Tool | Description |
|------|-------------|
| `post_report` | Publish HTML with title and visibility |
| `list_reports` | List reports by scope (`mine`, `shared`, `all`) |
| `set_report_visibility` | Toggle `private` / `shareable` |
| `get_report_url` | Get URL for an existing report |