#!/usr/bin/env bash
set -euo pipefail

PORT="${HUB_PORT:-8080}"

if ! command -v tailscale >/dev/null 2>&1; then
  echo "tailscale CLI not found. Install Tailscale first."
  exit 1
fi

echo "Exposing http://127.0.0.1:${PORT} on your tailnet..."
echo "Press Ctrl+C to stop."
echo ""
exec tailscale serve "${PORT}"