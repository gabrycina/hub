---
name: hub-publish
description: >
  Generate a self-contained HTML report and publish it to Hub via MCP.
  Use when the user wants to share an explanation, data review, context doc,
  or report with colleagues. Triggers on: "post report", "publish to hub",
  "share this report", "hub report", or after generating HTML artifacts for
  team sharing.
---

# Hub Publish

Publish rich HTML reports to a Hub instance and return a shareable link.

Hub can be hosted three ways (transparent to publishing): **local** (the user's
machine over Tailscale Serve), **server** (a shared always-on box reached over a
VPN/tailnet), or **connect** (the agent points at someone else's shared Hub).
`post_report` works the same in all three — it returns the report's `url`.

## Workflow

1. **Confirm visibility** if the user did not specify:
   - `private` — default for sensitive or draft content
   - `shareable` — visible to others
   - Note: in **server mode** the network (VPN/tailnet) is the access boundary, so
     anyone who can reach the server sees every report regardless of visibility.
     Warn before publishing sensitive content to a shared server.

2. **Generate HTML** using `skills/hub-publish/template.html` as the shell:
   - Replace `{{title}}`, `{{body}}`, `{{generated_at}}`
   - Keep report CSS inline; the template loads Mermaid from CDN for diagrams
   - **Mermaid diagrams** — use `<pre class="mermaid">`, not markdown fences. Escape `&` as `&amp;` in node chains (e.g. `A &amp; B`). Keep each node label on ONE line — never put `<br/>` inside a label: a `<pre>` turns it into a real newline and Mermaid fails with "Syntax error in text". Hub themes Mermaid by the viewer's OS dark/light setting, which can clash with a fixed page background (e.g. dark nodes on a white page). To pin the diagram's colors, make the first line of the block a theme directive, e.g. `%%{init: {'theme':'neutral'}}%%` for a light page or `'dark'` for a dark one.
     ```html
     <pre class="mermaid">
     flowchart LR
       A[Start] --> B[End]
     </pre>
     ```

3. **Publish** via MCP tool `post_report`:
   ```
   post_report(
     html=<full html string>,
     title=<descriptive title>,
     visibility="private" | "shareable",
     tags=[...],        # optional
     project=<name>     # optional
   )
   ```

4. **Open, then return**:
   - **Open the report in the user's browser by default** so it pops up without
     them clicking (macOS: `open <url>`, Linux: `xdg-open <url>`, Windows:
     `start <url>`), and copy the link to the clipboard where possible
     (macOS: `printf %s <url> | pbcopy`). Skip auto-open only if the user has
     said they don't want it.
   - Then tell them the `url`, that it's reachable on the tailnet/VPN (not the
     public internet), and the visibility used.

## Content guidelines

- Use clear headings and scannable sections
- Tables for structured data; keep columns readable
- Add a short summary at the top
- For flowcharts, sequence diagrams, or architecture sketches, use Mermaid blocks (see above)
- For sensitive data, default to `private` and warn before sharing

## If MCP is unavailable

The Hub MCP isn't registered yet. Pick the mode that fits, then ask the user to
restart their agent (see the repo `README.md` for details):

```bash
cd /path/to/hub && uv sync

# Local: host on this machine over Tailscale Serve
uv run hub init --mcp

# Connect: use a shared Hub someone else runs (no local server)
uv run hub connect --url http://<server>:8000 --token <token> --mcp
```

See the **Troubleshooting** section in the README if tools still don't appear.
