<p align="center">
  <img src="docs/icon.png" alt="Hub" width="96" height="96">
</p>

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

### Step 2 — Initialize Hub, MCP, and Tailscale Serve

```bash
uv run hub init --mcp
```

This automatically:
- Creates `~/.config/hub/` (token, config, data)
- Registers MCP with detected agents (Claude Code, Cursor, Grok Build, Codex)
- Starts Hub
- Sets up **Tailscale Serve** (opens the one-time enable link if needed)

**If a browser opens:** the user must approve Tailscale Serve on their tailnet (one-time). Hub waits up to 90 seconds, then prints the enable URL if still pending.

**Tell the user:** restart whichever agents were configured (e.g. Grok Build, Codex, Claude Code).

If Serve wasn't enabled in time:

```bash
uv run hub serve-setup
```

### Step 3 — Install the publish skill (recommended)

Copy the skill into the user's project so you know how to format and publish reports:

```bash
mkdir -p .claude/skills/hub-publish
cp /path/to/hub/skills/hub-publish/SKILL.md .claude/skills/hub-publish/
cp /path/to/hub/skills/hub-publish/template.html .claude/skills/hub-publish/
```

Or for a global skill (all projects):

```bash
# Grok Build
mkdir -p ~/.grok/skills/hub-publish
cp /path/to/hub/skills/hub-publish/* ~/.grok/skills/hub-publish/

# Claude Code (Grok also reads this path)
mkdir -p ~/.claude/skills/hub-publish
cp /path/to/hub/skills/hub-publish/* ~/.claude/skills/hub-publish/
```

### Step 4 — Verify

After the user restarts their agent, confirm MCP tools are available. You should see:

- `post_report`
- `list_reports`
- `set_report_visibility`
- `get_report_url`

If tools are missing, see [Troubleshooting](#troubleshooting).

### Step 5 — Verify Tailscale Serve

```bash
uv run hub status
```

| `serve:` value | Meaning |
|----------------|---------|
| `active` | `.ts.net` links work |
| `needs_enable` | User must open `enable_url` and run `uv run hub serve-setup` |
| `local_only` | No Tailscale — localhost only |

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

### Share links don't work / ERR_CONNECTION_REFUSED on .ts.net

Tailscale Serve is not active. Check:

```bash
uv run hub status
```

If `serve: needs_enable`, open the `enable_url` and run:

```bash
uv run hub serve-setup
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
uv run hub init --mcp       # one-time setup: MCP + Tailscale Serve
uv run hub serve-setup      # retry Tailscale Serve after enabling
uv run hub up               # start hub + configure serve
uv run hub up --no-serve    # start hub locally only
uv run hub status           # check hub + serve state
```

---

## For humans

**First time:**

```bash
cd hub
uv sync && uv run hub init --mcp
```

Approve Tailscale Serve if your browser opens. Restart Claude Code. Done.

If `.ts.net` links fail later: `uv run hub serve-setup`

---

## More docs

- [Tailscale setup](docs/tailscale.md)
- [MCP details](docs/mcp-claude-code.md)
- [Security model](docs/security.md)

## License

MIT