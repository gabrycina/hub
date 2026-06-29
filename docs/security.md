# Security model

## Network

- Hub binds to `127.0.0.1` only
- Expose via `tailscale serve`, not `0.0.0.0`
- Traffic stays on your tailnet by default

## Authentication

| Path | Auth method |
|------|-------------|
| Browser via Serve | `Tailscale-User-Login` header |
| MCP / API | `Authorization: Bearer <token>` |
| Local dev | `HUB_DEV_USER` when no Tailscale header present |

Tailscale Serve proxies to `127.0.0.1` and injects identity headers. Hub trusts `Tailscale-User-Login` when present. Binding to localhost only prevents remote header spoofing (see [Tailscale docs](https://tailscale.com/kb/1312/serve#identity-headers)).

## Visibility

- `private` — only the owner can view
- `shareable` — any authenticated tailnet user can view

Direct links to private reports still require owner auth.

## HTML content

Uploaded HTML is user-generated and may contain scripts. Hub previews content in a sandboxed iframe. The `/raw` endpoint serves content with `Content-Security-Policy: sandbox allow-scripts allow-same-origin` so diagrams (e.g. Mermaid) can render while staying sandboxed.

Treat uploaded reports like untrusted web content.

## Token storage

- API token: `~/.config/hub/token` (mode 600)
- Never commit tokens to git
- Rotate by deleting the token file and re-running `setup.sh`

## Recommendations

- Run Hub on a machine you control
- Default to `private` for sensitive reports
- Use shareable only when colleagues need access
- Do not expose Hub to the public internet