#!/bin/bash
#
# AI Sessions Sync Installer
# ==========================
# Installs sync scripts and sets up automatic syncing via launchd
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="$HOME"
LAUNCH_AGENTS_DIR="$HOME_DIR/Library/LaunchAgents"
PLIST_NAME="com.$(whoami).ai-sessions-sync.plist"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🔧 AI Sessions Sync Installer"
echo "=============================="
echo ""

# Copy scripts to home directory
echo -e "${YELLOW}📂 Copying sync scripts to home directory...${NC}"
cp "$SCRIPT_DIR/sync_ai_sessions_to_obsidian.py" "$HOME_DIR/"
cp "$SCRIPT_DIR/sync_claude_code_to_obsidian.py" "$HOME_DIR/"
cp "$SCRIPT_DIR/sync_codex_to_obsidian.py" "$HOME_DIR/"
cp "$SCRIPT_DIR/sync_cursor_to_obsidian.py" "$HOME_DIR/"
chmod +x "$HOME_DIR"/sync_*.py
echo -e "${GREEN}✓ Scripts copied${NC}"

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
echo "Useful commands:"
echo "  Manual sync:    python3 ~/sync_ai_sessions_to_obsidian.py"
echo "  View log:       cat ~/.ai-sessions-sync.log"
echo "  Check status:   launchctl list | grep ai-sessions-sync"
echo "  Stop auto-sync: launchctl unload ~/Library/LaunchAgents/$PLIST_NAME"
