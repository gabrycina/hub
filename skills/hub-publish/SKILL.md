---
name: hub-publish
description: >
  Generate a self-contained HTML report and publish it to Hub via MCP.
  Use when the user wants to share an explanation, data review, context doc,
  or report with colleagues on the tailnet. Triggers on: "post report",
  "publish to hub", "share this report", "hub report", or after generating
  HTML artifacts for team sharing.
---

# Hub Publish

Publish rich HTML reports to the user's Hub instance on their Tailnet.

## Workflow

1. **Confirm visibility** if the user did not specify:
   - `private` — default for sensitive or draft content
   - `shareable` — visible to colleagues on the tailnet

2. **Generate HTML** using `skills/hub-publish/template.html` as the shell:
   - Replace `{{title}}`, `{{body}}`, `{{generated_at}}`
   - Keep all CSS inline in the template
   - Self-contained: no external dependencies unless charts are needed

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

4. **Return to user**:
   - The Tailscale URL from the response
   - Reminder: tailnet-only, not public internet
   - Visibility setting used

## Content guidelines

- Use clear headings and scannable sections
- Tables for structured data; keep columns readable
- Add a short summary at the top
- For sensitive data, default to `private` and warn before sharing

## If MCP is unavailable

Tell the user to run `./scripts/setup.sh` and add the Hub MCP server to Claude Code.