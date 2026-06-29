# Tailscale setup

Hub uses Tailscale Serve to expose your local instance on your tailnet.

## Automatic (built into setup)

```bash
uv run hub init --mcp
```

This will:
1. Start Hub on `127.0.0.1:8080`
2. Configure `tailscale serve`
3. Open the **one-time** Tailscale Serve enable page if your tailnet hasn't approved it yet
4. Wait up to 90 seconds for you to approve
5. Save the correct `HUB_PUBLIC_URL` only when Serve is active

## If setup finishes before you approve Serve

```bash
uv run hub serve-setup
```

Check status anytime:

```bash
uv run hub status
```

Look for `serve: active` and a `https://your-machine.tailnet.ts.net` public URL.

## Local only (no Tailscale)

```bash
uv run hub init --mcp --no-serve
```

Report links will use `http://127.0.0.1:8080` until Serve is configured.

## Do not use Funnel

Keep Hub tailnet-only. Do not expose it with `tailscale funnel` unless you fully understand the security implications.