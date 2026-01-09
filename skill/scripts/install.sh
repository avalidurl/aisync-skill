#!/bin/bash
#
# AI Sessions Sync Installer
# ==========================
# Cross-platform installer for macOS, Linux, and Windows (Git Bash/WSL)
# Supports 12 AI coding agents
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="$HOME"
LOCAL_BIN="$HOME_DIR/.local/bin"

# Detect OS
detect_os() {
    case "$(uname -s)" in
        Darwin*)    echo "macos" ;;
        Linux*)     
            if grep -qi microsoft /proc/version 2>/dev/null; then
                echo "wsl"
            else
                echo "linux"
            fi
            ;;
        MINGW*|MSYS*|CYGWIN*)  echo "windows" ;;
        *)          echo "unknown" ;;
    esac
}

OS=$(detect_os)

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "🔧 AI Sessions Sync Installer"
echo "=============================="
echo "Detected OS: $OS"
echo ""

# Copy scripts to home directory
echo -e "${YELLOW}📂 Copying sync scripts to home directory...${NC}"

SCRIPTS=(
    "sync_ai_sessions_to_obsidian.py"
    "sync_claude_code_to_obsidian.py"
    "sync_codex_to_obsidian.py"
    "sync_cursor_to_obsidian.py"
    "sync_aider_to_obsidian.py"
    "sync_cline_to_obsidian.py"
    "sync_gemini_cli_to_obsidian.py"
    "sync_continue_to_obsidian.py"
    "sync_copilot_chat_to_obsidian.py"
    "sync_roo_code_to_obsidian.py"
    "sync_windsurf_to_obsidian.py"
    "sync_zed_ai_to_obsidian.py"
    "sync_amp_to_obsidian.py"
)

for script in "${SCRIPTS[@]}"; do
    cp "$SCRIPT_DIR/$script" "$HOME_DIR/"
done

chmod +x "$HOME_DIR"/sync_*.py
echo -e "${GREEN}✓ ${#SCRIPTS[@]} sync scripts copied${NC}"

# Install CLI tool
echo -e "${YELLOW}🔧 Installing aisync CLI...${NC}"
mkdir -p "$LOCAL_BIN"
cp "$SCRIPT_DIR/aisync" "$HOME_DIR/aisync"
chmod +x "$HOME_DIR/aisync"
ln -sf "$HOME_DIR/aisync" "$LOCAL_BIN/aisync"

# Add to PATH
for rc in ".zshrc" ".bashrc" ".bash_profile"; do
    if [ -f "$HOME_DIR/$rc" ]; then
        if ! grep -q '.local/bin' "$HOME_DIR/$rc" 2>/dev/null; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME_DIR/$rc"
        fi
    fi
done
echo -e "${GREEN}✓ CLI installed${NC}"

# Platform-specific scheduler setup
setup_scheduler() {
    case "$OS" in
        macos)
            setup_launchd
            ;;
        linux|wsl)
            setup_systemd_or_cron
            ;;
        windows)
            setup_windows_task
            ;;
        *)
            echo -e "${YELLOW}⚠️  Unknown OS - skipping auto-sync setup${NC}"
            echo "   Run manually: python3 ~/sync_ai_sessions_to_obsidian.py"
            ;;
    esac
}

setup_launchd() {
    echo -e "${YELLOW}📝 Setting up macOS launchd agent...${NC}"
    
    LAUNCH_AGENTS_DIR="$HOME_DIR/Library/LaunchAgents"
    PLIST_NAME="com.$(whoami).ai-sessions-sync.plist"
    
    mkdir -p "$LAUNCH_AGENTS_DIR"
    
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

    launchctl unload "$LAUNCH_AGENTS_DIR/$PLIST_NAME" 2>/dev/null || true
    launchctl load "$LAUNCH_AGENTS_DIR/$PLIST_NAME"
    echo -e "${GREEN}✓ launchd agent loaded${NC}"
}

setup_systemd_or_cron() {
    # Try systemd first (modern Linux)
    if command -v systemctl &> /dev/null && [ -d "$HOME_DIR/.config/systemd/user" ] || mkdir -p "$HOME_DIR/.config/systemd/user"; then
        echo -e "${YELLOW}📝 Setting up systemd user service...${NC}"
        
        # Create service file
        cat > "$HOME_DIR/.config/systemd/user/ai-sessions-sync.service" << EOF
[Unit]
Description=AI Sessions Sync to Obsidian
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 $HOME_DIR/sync_ai_sessions_to_obsidian.py
Environment=PATH=/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=default.target
EOF

        # Create timer file
        cat > "$HOME_DIR/.config/systemd/user/ai-sessions-sync.timer" << EOF
[Unit]
Description=Run AI Sessions Sync every 15 minutes

[Timer]
OnBootSec=5min
OnUnitActiveSec=15min
Persistent=true

[Install]
WantedBy=timers.target
EOF

        systemctl --user daemon-reload 2>/dev/null || true
        systemctl --user enable ai-sessions-sync.timer 2>/dev/null || true
        systemctl --user start ai-sessions-sync.timer 2>/dev/null || true
        echo -e "${GREEN}✓ systemd timer enabled${NC}"
    else
        # Fall back to cron
        echo -e "${YELLOW}📝 Setting up cron job...${NC}"
        
        CRON_CMD="*/15 * * * * /usr/bin/python3 $HOME_DIR/sync_ai_sessions_to_obsidian.py >> $HOME_DIR/.ai-sessions-sync.log 2>&1"
        
        # Add to crontab if not already there
        (crontab -l 2>/dev/null | grep -v "sync_ai_sessions_to_obsidian"; echo "$CRON_CMD") | crontab -
        echo -e "${GREEN}✓ cron job added (every 15 minutes)${NC}"
    fi
}

setup_windows_task() {
    echo -e "${YELLOW}📝 Windows detected...${NC}"
    echo ""
    echo "To set up automatic sync on Windows, run this in PowerShell as Administrator:"
    echo ""
    echo -e "${GREEN}\$action = New-ScheduledTaskAction -Execute 'python3' -Argument '\$env:USERPROFILE\\sync_ai_sessions_to_obsidian.py'${NC}"
    echo -e "${GREEN}\$trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 15) -Once -At (Get-Date)${NC}"
    echo -e "${GREEN}Register-ScheduledTask -TaskName 'AISyncObsidian' -Action \$action -Trigger \$trigger -Description 'Sync AI sessions to Obsidian'${NC}"
    echo ""
    echo "Or use Task Scheduler GUI to create a task that runs:"
    echo "  python3 %USERPROFILE%\\sync_ai_sessions_to_obsidian.py"
}

# Run scheduler setup
setup_scheduler

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
