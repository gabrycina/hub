from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "hub"
CONFIG_ENV = CONFIG_DIR / "config.env"
TOKEN_FILE = CONFIG_DIR / "token"
PID_FILE = CONFIG_DIR / "hub.pid"
LOCK_FILE = CONFIG_DIR / "hub.lock"
LOG_FILE = CONFIG_DIR / "hub.log"
DATA_DIR = CONFIG_DIR / "data"
CLAUDE_CONFIG = Path.home() / ".claude.json"
CURSOR_MCP = Path.home() / ".cursor" / "mcp.json"
GROK_CONFIG = Path.home() / ".grok" / "config.toml"
CODEX_CONFIG = Path.home() / ".codex" / "config.toml"