from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "hub"
CONFIG_ENV = CONFIG_DIR / "config.env"
TOKEN_FILE = CONFIG_DIR / "token"
PID_FILE = CONFIG_DIR / "hub.pid"
DATA_DIR = CONFIG_DIR / "data"
CLAUDE_MCP = Path.home() / ".claude" / ".mcp.json"