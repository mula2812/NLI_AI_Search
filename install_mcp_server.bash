#!/bin/bash
set -e
shopt -s globstar nullglob

# === Check Python 3.10+ installation ===
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 is not installed or not in PATH."
    exit 1
fi

PYVER=$(python3 --version 2>&1 | awk '{print $2}')
PY_MAJOR=$(echo "$PYVER" | cut -d. -f1)
PY_MINOR=$(echo "$PYVER" | cut -d. -f2)

if (( PY_MAJOR < 3 )) || { (( PY_MAJOR == 3 )) && (( PY_MINOR < 10 )); }; then
    echo "ERROR: Python version is less than 3.10. Please install Python 3.10 or higher."
    exit 1
fi

echo "Python version $PYVER detected, OK."

# === Install Python requirements ===
# Assuming requirements.txt is in the same folder as this script
SCRIPT_DIR="$(dirname "$(realpath "$0")")"
REQ_FILE="$SCRIPT_DIR/requirements.txt"

if [ ! -f "$REQ_FILE" ]; then
    echo "ERROR: requirements.txt not found at $REQ_FILE"
    exit 1
fi

echo "Installing Python packages from $REQ_FILE..."
python3 -m pip install --upgrade pip
python3 -m pip install -r "$REQ_FILE"

echo "Python requirements installed successfully."

# === 1) Locate nli_mcp.py ===
SRV_PATH=""
for f in "$SCRIPT_DIR"/**/nli_mcp.py; do
    SRV_PATH="$(realpath "$f")"
    break
done

if [ -z "$SRV_PATH" ]; then
    echo "ERROR: nli_mcp.py not found."
    exit 1
fi

echo "Found nli_mcp.py at: $SRV_PATH"

# === 2) Set environment variable ===
export NLI_API_KEY="DVQyidFLOAjp12ib92pNJPmflmB5IessOq1CJQDK"
echo "Environment variable NLI_API_KEY set."

# === 3) Install ===
if ! fastmcp install claude-desktop "$SRV_PATH" --server-name "nli_mcp" --env NLI_API_KEY="$NLI_API_KEY"; then
    echo "ERROR: fastmcp install failed."
    exit 1
fi
echo "fastmcp install completed."

# === 4) Modify JSON config ===
CONFIG="$HOME/.config/Claude/claude_desktop_config.json"

if [ ! -f "$CONFIG" ]; then
    echo "ERROR: Config file not found: $CONFIG"
    exit 1
fi

echo "Modifying JSON config: $CONFIG"

python3 - <<EOF
import json, os

config_path = os.path.expanduser("$CONFIG")
srv_path = "$SRV_PATH"
api_key = os.getenv("NLI_API_KEY", "")

try:
    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
        cfg = json.loads(content) if content else {}
except Exception:
    cfg = {}

cfg.setdefault("mcpServers", {})
cfg["mcpServers"].setdefault("nli_mcp", {})
cfg["mcpServers"]["nli_mcp"]["command"] = "python3"
cfg["mcpServers"]["nli_mcp"]["args"] = [srv_path]
cfg["mcpServers"]["nli_mcp"].setdefault("env", {})["NLI_API_KEY"] = api_key
cfg["mcpServers"]["nli_mcp"]["transport"] = "stdio"

with open(config_path, "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2)

print("JSON config updated.")
EOF

echo
echo "Done. Please restart Claude Desktop to apply changes."