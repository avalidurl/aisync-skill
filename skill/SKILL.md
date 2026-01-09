---
name: aisync
description: Sync AI coding sessions (Claude Code, Codex CLI, Cursor) to Obsidian vault as markdown notes. Use when user wants to backup, export, or sync their AI chat sessions to Obsidian, set up automatic syncing via launchd, check sync status, or troubleshoot sync issues. Handles secret redaction automatically.
---

# AI Sessions Sync to Obsidian

Sync Claude Code, Codex CLI, and Cursor agent sessions to an Obsidian Zettelkasten vault as markdown notes with automatic secret redaction.

## Quick Reference

| Source | Location | Output Folder |
|--------|----------|---------------|
| Claude Code | `~/.claude/projects/**/*.jsonl` | `ai-sessions/claude-code-sessions/` |
| Codex CLI | `~/.codex/sessions/**/*.jsonl` | `ai-sessions/codex-sessions/` |
| Cursor | `~/.cursor/projects/**/agent-transcripts/*.txt` | `ai-sessions/cursor-sessions/` |

## Manual Sync

Run the unified sync script:

```bash
python3 ~/sync_ai_sessions_to_obsidian.py
```

Or run individual syncs:

```bash
python3 ~/sync_claude_code_to_obsidian.py
python3 ~/sync_codex_to_obsidian.py
python3 ~/sync_cursor_to_obsidian.py
```

## Automatic Sync Setup (launchd)

### Create the LaunchAgent plist

Create `~/Library/LaunchAgents/com.USER.ai-sessions-sync.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.USER.ai-sessions-sync</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>HOMEDIR/sync_ai_sessions_to_obsidian.py</string>
    </array>
    <key>StartInterval</key>
    <integer>900</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>HOMEDIR/.ai-sessions-sync-stdout.log</string>
    <key>StandardErrorPath</key>
    <string>HOMEDIR/.ai-sessions-sync-stderr.log</string>
</dict>
</plist>
```

Replace `USER` with username and `HOMEDIR` with full home path (e.g., `/Users/john`).

### Load/Unload Commands

```bash
# Load (start auto-sync)
launchctl load ~/Library/LaunchAgents/com.USER.ai-sessions-sync.plist

# Unload (stop auto-sync)
launchctl unload ~/Library/LaunchAgents/com.USER.ai-sessions-sync.plist

# Check status
launchctl list | grep ai-sessions-sync

# View logs
cat ~/.ai-sessions-sync.log
tail -f ~/.ai-sessions-sync-stdout.log
```

## Interval Configuration

Change `<integer>900</integer>` in the plist:

| Interval | Seconds |
|----------|---------|
| 5 min | 300 |
| 15 min | 900 |
| 30 min | 1800 |
| 1 hour | 3600 |

After changing, unload and reload the agent.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No sessions found | Check source paths exist: `ls ~/.claude/projects`, `ls ~/.codex/sessions`, `ls ~/.cursor/projects` |
| Sync not running | Verify agent loaded: `launchctl list \| grep ai-sessions` |
| Permission errors | Ensure scripts are executable: `chmod +x ~/sync_*.py` |
| Vault not found | Update `OBSIDIAN_VAULT` path in sync scripts |

## Scripts

The skill includes these scripts in `scripts/`:

- `sync_ai_sessions_to_obsidian.py` - Unified sync runner
- `sync_claude_code_to_obsidian.py` - Claude Code sessions
- `sync_codex_to_obsidian.py` - Codex CLI sessions  
- `sync_cursor_to_obsidian.py` - Cursor agent sessions

Run `scripts/install.sh` to copy scripts to home directory and set up the launchd agent.
