#!/bin/bash
#
# AI Sessions Sync Installer
# ==========================
# Installs sync scripts and sets up automatic syncing via launchd
# Supports 12 AI coding agents: Claude Code, Codex, Cursor, Aider, Cline,
# Gemini CLI, Continue.dev, GitHub Copilot, Roo Code, Windsurf, Zed AI, Amp
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="$HOME"
LAUNCH_AGENTS_DIR="$HOME_DIR/Library/LaunchAgents"
PLIST_NAME="com.$(whoami).ai-sessions-sync.plist"
LOCAL_BIN="$HOME_DIR/.local/bin"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🔧 AI Sessions Sync Installer"
echo "=============================="
echo ""

# Copy scripts to home directory
echo -e "${YELLOW}📂 Copying sync scripts to home directory...${NC}"

# Core scripts
cp "$SCRIPT_DIR/sync_ai_sessions_to_obsidian.py" "$HOME_DIR/"
cp "$SCRIPT_DIR/sync_claude_code_to_obsidian.py" "$HOME_DIR/"
cp "$SCRIPT_DIR/sync_codex_to_obsidian.py" "$HOME_DIR/"
cp "$SCRIPT_DIR/sync_cursor_to_obsidian.py" "$HOME_DIR/"

# Additional providers
cp "$SCRIPT_DIR/sync_aider_to_obsidian.py" "$HOME_DIR/"
cp "$SCRIPT_DIR/sync_cline_to_obsidian.py" "$HOME_DIR/"
cp "$SCRIPT_DIR/sync_gemini_cli_to_obsidian.py" "$HOME_DIR/"
cp "$SCRIPT_DIR/sync_continue_to_obsidian.py" "$HOME_DIR/"
cp "$SCRIPT_DIR/sync_copilot_chat_to_obsidian.py" "$HOME_DIR/"
cp "$SCRIPT_DIR/sync_roo_code_to_obsidian.py" "$HOME_DIR/"
cp "$SCRIPT_DIR/sync_windsurf_to_obsidian.py" "$HOME_DIR/"
cp "$SCRIPT_DIR/sync_zed_ai_to_obsidian.py" "$HOME_DIR/"
cp "$SCRIPT_DIR/sync_amp_to_obsidian.py" "$HOME_DIR/"

chmod +x "$HOME_DIR"/sync_*.py
echo -e "${GREEN}✓ 13 sync scripts copied${NC}"

# Install CLI tool
echo -e "${YELLOW}🔧 Installing aisync CLI...${NC}"
mkdir -p "$LOCAL_BIN"
cp "$SCRIPT_DIR/aisync" "$HOME_DIR/aisync"
chmod +x "$HOME_DIR/aisync"
ln -sf "$HOME_DIR/aisync" "$LOCAL_BIN/aisync"

# Add to PATH if not already there
if ! grep -q '.local/bin' "$HOME_DIR/.zshrc" 2>/dev/null; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME_DIR/.zshrc"
fi
if ! grep -q '.local/bin' "$HOME_DIR/.bashrc" 2>/dev/null; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME_DIR/.bashrc" 2>/dev/null || true
fi
echo -e "${GREEN}✓ CLI installed (run 'aisync help' for usage)${NC}"

# Create LaunchAgents directory if needed
mkdir -p "$LAUNCH_AGENTS_DIR"

# Create plist file
echo -e "${YELLOW}📝 Creating launchd agent...${NC}"
cat > "$LAUNCH_AGENTS_DIR/$PLIST_NAME" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.$(whoami).ai-sessions-sync</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>$HOME_DIR/sync_ai_sessions_to_obsidian.py</string>
    </array>
    <key>StartInterval</key>
    <integer>900</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$HOME_DIR/.ai-sessions-sync-stdout.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME_DIR/.ai-sessions-sync-stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
EOF
echo -e "${GREEN}✓ Plist created at $LAUNCH_AGENTS_DIR/$PLIST_NAME${NC}"

# Load the agent
echo -e "${YELLOW}🚀 Loading launchd agent...${NC}"
launchctl unload "$LAUNCH_AGENTS_DIR/$PLIST_NAME" 2>/dev/null || true
launchctl load "$LAUNCH_AGENTS_DIR/$PLIST_NAME"
echo -e "${GREEN}✓ Agent loaded${NC}"

# Run initial sync
echo -e "${YELLOW}🔄 Running initial sync...${NC}"
python3 "$HOME_DIR/sync_ai_sessions_to_obsidian.py"

echo ""
echo -e "${GREEN}✅ Installation complete!${NC}"
echo ""
echo "Sync will run automatically every 15 minutes."
echo ""
echo "📋 CLI Commands:"
echo "  aisync status        Show sync status"
echo "  aisync sync          Run sync now"
echo "  aisync interval 5    Set interval to 5 minutes"
echo "  aisync providers     List all providers"
echo "  aisync logs          View recent logs"
echo "  aisync help          Show all commands"
echo ""
echo "🔌 Supported Providers (12):"
echo "  Claude Code, Codex CLI, Cursor, Aider, Cline, Gemini CLI,"
echo "  Continue.dev, GitHub Copilot, Roo Code, Windsurf, Zed AI, Amp"
