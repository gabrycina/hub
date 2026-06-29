# Hub

**Your personal report inbox.** Publish HTML reports from Claude Code, browse them on a dashboard, and share with colleagues on your Tailnet.

---

## For agents: start here

If you're helping a user set up or use Hub, follow this guide step by step. You can run the commands yourself — don't just tell the user what to run.

### What Hub does

Hub stores HTML reports the agent generates. After publishing, the user gets a link they can open or share with colleagues on the company Tailnet.

```
You generate HTML  →  MCP post_report  →  user gets a link
```

### Is Hub already set up?

Run this from the hub repo:

```bash
uv run hub status
```

| Output | Meaning | What to do |
|--------|---------|------------|
| `initialized: false` | First time | Run setup (below) |
| `initialized: true`, `running: false` | Configured but not started | Fine — MCP auto-starts it. Or run `uv run hub up` |
| `initialized: true`, `running: true` | Ready | Skip setup, go publish |

Also check MCP is registered:

```bash
cat ~/.claude/.mcp.json | grep -q '"hub"' && echo "MCP registered" || echo "MCP missing"
```

---

## Agent setup guide (one-time)

Do this when the user wants Hub but it's not set up yet.

### Prerequisites

- **uv** installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **Tailscale** connected (for sharing with colleagues — optional for local-only use)
- **Claude Code** as the agent host

### Step 1 — Install dependencies

```bash
cd /path/to/hub
uv sync
```

### Step 2 — Initialize Hub + register MCP

```bash
uv run hub init --mcp
```

This automatically:
- Creates `~/.config/hub/` (token, config, data)
- Detects the user's Tailscale identity and machine URL
- Writes the MCP entry to `~/.claude/.mcp.json`

**Tell the user:** "Restart Claude Code so the Hub MCP server loads."

### Step 3 — Install the publish skill (recommended)

Copy the skill into the user's project so you know how to format and publish reports:

```bash
mkdir -p .claude/skills/hub-publish
cp /path/to/hub/skills/hub-publish/SKILL.md .claude/skills/hub-publish/
cp /path/to/hub/skills/hub-publish/template.html .claude/skills/hub-publish/
```

Or for a global skill (all projects):

```bash
mkdir -p ~/.claude/skills/hub-publish
cp /path/to/hub/skills/hub-publish/* ~/.claude/skills/hub-publish/
```

### Step 4 — Verify

After the user restarts Claude Code, confirm MCP tools are available. You should see:

- `post_report`
- `list_reports`
- `set_report_visibility`
- `get_report_url`

If tools are missing, see [Troubleshooting](#troubleshooting).

### Step 5 — Enable sharing (only if needed)

If the user wants colleagues to open report links, run:

```bash
uv run hub up
```

This starts Hub and exposes it on the Tailnet via `tailscale serve`. **Skip this** if the user only needs local reports for now.

---

## Agent: how to publish a report

Use this whenever the user asks to share an explanation, data review, context doc, or report.

### 1. Ask about visibility (if unclear)

| Visibility | Who can see it |
|------------|----------------|
| `private` | Only the owner (default — use for sensitive data) |
| `shareable` | Anyone on the Tailnet with the link |

### 2. Generate HTML

Use `skills/hub-publish/template.html` as the shell. Replace:

- `{{title}}` — report title
- `{{body}}` — your content (headings, tables, code, etc.)
- `{{generated_at}}` — current date/time

Keep CSS inline. Self-contained HTML only.

### 3. Publish via MCP

```
post_report(
  html=<full html string>,
  title="Q2 Metrics Dashboard",
  visibility="shareable",
  tags=["metrics", "q2"],
  project="growth"
)
```

### 4. Return the link to the user

The response includes a `url` field. Give them that link and note:

- It's **Tailnet-only** (not public internet)
- They can browse all reports at their Hub dashboard URL
- Use `set_report_visibility` to change private ↔ shareable later

### Example message to user

> Published **Q2 Metrics Dashboard** as shareable.
> Open it here: https://your-mac.your-tailnet.ts.net/a/abc123
> Colleagues on the Tailnet can view it too. It's not on the public internet.

---

## MCP tools reference

| Tool | When to use |
|------|-------------|
| `post_report` | Publish a new HTML report |
| `list_reports` | Find existing reports (`scope`: `mine`, `shared`, `all`) |
| `set_report_visibility` | Toggle `private` / `shareable` |
| `get_report_url` | Get the link for an existing report |

No env vars needed in MCP config — everything loads from `~/.config/hub/config.env`.

---

## Troubleshooting

**Agent: work through these in order.**

### MCP tools not showing up

1. Check config exists: `ls ~/.config/hub/config.env`
2. Check MCP registered: `cat ~/.claude/.mcp.json`
3. Re-run setup: `uv run hub init --mcp`
4. Ask user to **restart Claude Code**

### `post_report` fails with "not configured"

```bash
uv run hub init --mcp
```

Then restart Claude Code.

### `post_report` fails with connection error

Hub isn't running. It should auto-start, but you can start it manually:

```bash
uv run hub up --no-serve
```

### Share links don't work for colleagues

Colleagues need Tailnet access, and Hub needs to be exposed:

```bash
uv run hub up
```

Also confirm the report visibility is `shareable`, not `private`.

### Wrong URL in response

Re-detect Tailscale URL and re-init:

```bash
uv run hub init --mcp
```

---

## Commands cheat sheet

```bash
uv run hub init --mcp    # one-time setup + MCP registration
uv run hub up            # start hub + expose on tailnet
uv run hub up --no-serve # start hub locally only
uv run hub status        # check if configured and running
```

---

## For humans

**First time:**

```bash
cd hub
uv sync && uv run hub init --mcp
```

Restart Claude Code. Ask your agent to publish a report — Hub handles the rest.

**To share with colleagues:**

```bash
uv run hub up
```

That's the whole setup.

---

## More docs

- [Tailscale setup](docs/tailscale.md)
- [MCP details](docs/mcp-claude-code.md)
- [Security model](docs/security.md)

## License

MIT