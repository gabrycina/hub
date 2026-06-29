#!/usr/bin/env bash
set -euo pipefail

CONFIG_DIR="${HOME}/.config/hub"
DATA_DIR="${CONFIG_DIR}/data"
TOKEN_FILE="${CONFIG_DIR}/token"
CONFIG_FILE="${CONFIG_DIR}/config.env"

mkdir -p "${DATA_DIR}/artifacts"

if [[ ! -f "${TOKEN_FILE}" ]]; then
  TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
  echo "${TOKEN}" > "${TOKEN_FILE}"
  chmod 600 "${TOKEN_FILE}"
  echo "Created API token at ${TOKEN_FILE}"
else
  TOKEN="$(cat "${TOKEN_FILE}")"
  echo "Using existing API token at ${TOKEN_FILE}"
fi

OWNER="${HUB_OWNER:-}"
if [[ -z "${OWNER}" ]] && command -v tailscale >/dev/null 2>&1; then
  OWNER="$(tailscale whoami 2>/dev/null || true)"
fi
OWNER="${OWNER:-local@dev}"

PUBLIC_URL="${HUB_PUBLIC_URL:-}"
if [[ -z "${PUBLIC_URL}" ]] && command -v tailscale >/dev/null 2>&1; then
  PUBLIC_URL="$(tailscale status --json 2>/dev/null | python3 -c '
import json, os, sys
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
self_node = data.get("Self", {})
dns = self_node.get("DNSName", "").rstrip(".")
if dns:
    print(f"https://{dns}")
' || true)"
fi
PUBLIC_URL="${PUBLIC_URL:-http://127.0.0.1:8080}"

cat > "${CONFIG_FILE}" <<EOF
HUB_DATA_DIR=${DATA_DIR}
HUB_OWNER=${OWNER}
HUB_API_TOKEN=${TOKEN}
HUB_PUBLIC_URL=${PUBLIC_URL}
HUB_DEV_USER=${OWNER}
EOF
chmod 600 "${CONFIG_FILE}"

echo ""
echo "Hub setup complete."
echo ""
echo "Config: ${CONFIG_FILE}"
echo "Owner:  ${OWNER}"
echo "URL:    ${PUBLIC_URL}"
echo ""
echo "Run the hub:"
echo "  set -a && source ${CONFIG_FILE} && set +a && uv run hub"
echo ""
echo "Expose on your tailnet:"
echo "  ./scripts/tailscale-serve.sh"
echo ""
echo "Claude Code MCP config:"
cat <<EOF
{
  "mcpServers": {
    "hub": {
      "command": "uv",
      "args": ["--directory", "$(pwd)", "run", "hub-mcp"],
      "env": {
        "HUB_URL": "http://127.0.0.1:8080",
        "HUB_API_TOKEN": "${TOKEN}",
        "HUB_PUBLIC_URL": "${PUBLIC_URL}"
      }
    }
  }
}
EOF