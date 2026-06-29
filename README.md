<p align="center">
  <img src="docs/icon.png" alt="Hub" width="96" height="96">
</p>

<p align="center">
  Your personal report inbox on the Tailnet.<br>
  Agents publish HTML. You browse, search, and share — privately.
</p>

---

## What is this?

Hub is a tiny self-hosted app that collects HTML reports your AI agents write — architecture notes, data reviews, postmortems, anything worth keeping.

You get a clean dashboard called **Your Hub**, plus shareable links for colleagues on your company Tailnet. Nothing hits the public internet.

```mermaid
flowchart LR
  A[You + your agent] -->|writes HTML| B[Hub]
  B --> C[Your Hub dashboard]
  B -->|shareable link| D[Colleagues on Tailnet]
```

---

## Setup (2 minutes)

**You need:** [uv](https://docs.astral.sh/uv/), Tailscale connected (for sharing), and an agent host like Claude Code or Grok Build.

```bash
git clone https://github.com/gabrycina/hub.git
cd hub
uv sync && uv run hub init --mcp
```

That's it. Hub will:

1. Create `~/.config/hub/` (config, token, reports)
2. Register MCP with your agents
3. Start the server at **http://127.0.0.1:17482**
4. Set up **Tailscale Serve** for `.ts.net` links

If a browser tab opens, approve Tailscale Serve once — then restart your agent.

**Tailnet links not working?**

```bash
uv run hub serve-setup
```

**Check everything:**

```bash
uv run hub status
```

Look for `running: true` and `serve: active`.

---

## Daily use

| What | How |
|------|-----|
| Browse your reports | Open **Your Hub** at your local or `.ts.net` URL |
| Publish a report | Ask your agent: *"Publish this to Hub"* |
| Share with a colleague | Agent sets visibility to `shareable` — send them the link |
| Keep something private | Default is `private` — only you see it |

Local dashboard: **http://127.0.0.1:17482**

---

## Commands

```bash
uv run hub init --mcp       # one-time setup
uv run hub serve-setup      # retry Tailscale Serve
uv run hub up               # start + configure serve
uv run hub up --no-serve    # local only
uv run hub status           # health check
```

Port **17482** by default. Override with `HUB_PORT` in `~/.config/hub/config.env`.

---

## More docs

- [Tailscale setup](docs/tailscale.md)
- [MCP details](docs/mcp-claude-code.md)
- [Security model](docs/security.md)

MIT · [github.com/gabrycina/hub](https://github.com/gabrycina/hub)

---

# For agents

If you're setting up or using Hub on behalf of a user, follow this section. **Run commands yourself** — don't just tell the user what to run.

## Quick check

```bash
uv run hub status
```

| Output | Action |
|--------|--------|
| `initialized: false` | Run setup below |
| `initialized: true`, `running: false` | MCP auto-starts Hub; or `uv run hub up` |
| `initialized: true`, `running: true` | Ready — publish |

Verify MCP is registered:

```bash
grep -q '"hub"' ~/.claude/.mcp.json 2>/dev/null && echo "ok" || echo "missing"
```

(Grok Build, Cursor, and Codex use their own MCP paths — `hub init --mcp` writes to all detected agents.)

## One-time setup

```bash
cd /path/to/hub
uv sync
uv run hub init --mcp
```

This creates config, registers MCP, starts Hub, and configures Tailscale Serve. If Serve needs approval, a browser link opens — wait for the user, then `uv run hub serve-setup` if needed.

**Tell the user** to restart their agent after init.

### Install the publish skill (recommended)

```bash
mkdir -p ~/.grok/skills/hub-publish ~/.claude/skills/hub-publish
cp skills/hub-publish/* ~/.grok/skills/hub-publish/
cp skills/hub-publish/* ~/.claude/skills/hub-publish/
```

Or per-project: `.claude/skills/hub-publish/`

### Verify MCP tools

You should see: `post_report`, `list_reports`, `set_report_visibility`, `get_report_url`

## Publishing a report

1. **Ask visibility** if unclear: `private` (default) or `shareable` (Tailnet colleagues)
2. **Generate HTML** from `skills/hub-publish/template.html` — replace `{{title}}`, `{{body}}`, `{{generated_at}}`. Keep CSS inline. For Mermaid, use `<pre class="mermaid">` and escape `&` as `&amp;`.
3. **Publish:**

```
post_report(
  html=<full html>,
  title="Q2 Metrics Dashboard",
  visibility="shareable",
  tags=["metrics"],
  project="growth"
)
```

4. **Return the `url`** from the response. Remind: Tailnet-only, not public internet.

## MCP tools

| Tool | Use |
|------|-----|
| `post_report` | Publish HTML |
| `list_reports` | List reports (`scope`: `mine`, `shared`, `all`) |
| `set_report_visibility` | Toggle `private` / `shareable` |
| `get_report_url` | Get link for existing report |

No env vars in MCP config — loads from `~/.config/hub/config.env`.

## Troubleshooting

**Tools missing** → `uv run hub init --mcp`, restart agent

**`post_report` connection error** → `uv run hub up --no-serve`

**`.ts.net` link fails** → `uv run hub status`, check `serve: needs_enable`, run `uv run hub serve-setup`

**Wrong URL** → `uv run hub init --mcp` to re-detect Tailscale URL

**Report not visible to colleague** → visibility must be `shareable`, not `private`