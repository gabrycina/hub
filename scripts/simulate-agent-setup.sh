#!/usr/bin/env bash
# Simulates what a Claude Code agent does to set up Hub from scratch.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SANDBOX="${SANDBOX:-$(mktemp -d /tmp/hub-sim-XXXXXX)}"
export HOME="$SANDBOX"
if [ -z "${HUB_PORT:-}" ]; then
  HUB_PORT="$(python3 -c "import socket; s=socket.socket(); s.bind(('', 0)); print(s.getsockname()[1]); s.close()")"
  export HUB_PORT
fi
export PYTHONPATH="$REPO_ROOT"

cleanup() {
  if [ -f "$HOME/.config/hub/hub.pid" ]; then
    kill "$(cat "$HOME/.config/hub/hub.pid")" 2>/dev/null || true
  fi
}
trap cleanup EXIT

cd "$REPO_ROOT"
HUB="$REPO_ROOT/.venv/bin/hub"

echo "=== Agent simulation sandbox: $SANDBOX (port $HUB_PORT) ==="
echo "=== Step 1: uv sync ==="
uv sync -q

echo "=== Step 2: hub status (before init) ==="
"$HUB" status

echo "=== Step 3: hub init --mcp ==="
"$HUB" init --mcp --no-open --serve-wait 8 || true

echo "=== Step 4: verify config + MCP ==="
cat "$HOME/.config/hub/config.env"
echo "---"
cat "$HOME/.claude/.mcp.json"

echo "=== Step 5: hub status ==="
"$HUB" status

echo "=== Step 6: copy hub-publish skill ==="
mkdir -p "$HOME/.claude/skills/hub-publish"
cp "$REPO_ROOT/skills/hub-publish/"* "$HOME/.claude/skills/hub-publish/"

echo "=== Step 7: post_report via API (MCP equivalent) ==="
TOKEN=$(grep HUB_API_TOKEN "$HOME/.config/hub/config.env" | cut -d= -f2-)
RESPONSE=$(curl -s -X POST "http://127.0.0.1:${HUB_PORT}/api/artifacts" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"html":"<!DOCTYPE html><html><body><h1>Agent simulation</h1></body></html>","title":"Agent Sim Report","visibility":"shareable","tags":["sim"]}')
echo "$RESPONSE" | python3 -m json.tool
REPORT_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "=== Step 8: list_reports via API ==="
curl -s "http://127.0.0.1:${HUB_PORT}/api/artifacts?scope=all" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo "=== Step 9: dashboard + preview ==="
curl -s -o /dev/null -w "dashboard: HTTP %{http_code}\n" "http://127.0.0.1:${HUB_PORT}/"
curl -s -o /dev/null -w "preview:  HTTP %{http_code}\n" "http://127.0.0.1:${HUB_PORT}/a/${REPORT_ID}"

echo "=== Simulation complete ==="
echo "Sandbox: $SANDBOX"