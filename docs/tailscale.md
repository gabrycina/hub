# Tailscale setup

Hub binds to `127.0.0.1` and is exposed to your tailnet via Tailscale Serve.

## Automatic (recommended)

```bash
uv run hub up
```

This starts Hub and runs `tailscale serve` in the background.

## Manual

```bash
uv run hub up --no-serve   # local only
tailscale serve 8080       # expose separately if needed
```

## Identity headers

Serve injects `Tailscale-User-Login` on every request. Hub uses this for dashboard auth.

Set `HUB_PUBLIC_URL` in `~/.config/hub/config.env` (auto-detected during `hub init`) so MCP returns correct share links.

## Do not use Funnel

Keep Hub tailnet-only. Do not expose it with `tailscale funnel` unless you fully understand the security implications.