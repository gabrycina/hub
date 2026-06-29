# Tailscale setup

Hub is designed to run on `127.0.0.1` and be exposed to your tailnet with Tailscale Serve.

## Prerequisites

- Tailscale installed and connected
- HTTPS certificates enabled in your tailnet

## Expose Hub

```bash
uv run hub                  # listens on 127.0.0.1:8080
./scripts/tailscale-serve.sh
```

Tailscale prints your tailnet URL, e.g. `https://your-mac.your-tailnet.ts.net`.

Set that as `HUB_PUBLIC_URL` in `~/.config/hub/config.env` so MCP returns correct share links.

## Identity headers

Serve injects `Tailscale-User-Login` on every request. Hub uses this for dashboard auth — no separate login form.

Hub only trusts these headers when traffic arrives through Serve (non-localhost). Direct localhost access uses `HUB_DEV_USER` or API token auth.

## Do not use Funnel

Keep Hub tailnet-only. Do not expose it with `tailscale funnel` unless you fully understand the security implications.