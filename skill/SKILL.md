---
name: aisync
description: Sync AI coding sessions from 12 tools (Claude Code, Codex, Cursor, Aider, Cline, Gemini CLI, Continue, Copilot, Roo Code, Windsurf, Zed AI, Amp) to Obsidian vault as markdown notes. Use when user wants to backup, export, or sync their AI chat sessions to Obsidian, set up automatic syncing, check sync status, or troubleshoot sync issues. Handles secret redaction automatically. Cross-platform (macOS, Linux, Windows).
---

# AI Sessions Sync to Obsidian

Sync AI coding sessions from **12 different tools** to an Obsidian vault as markdown notes with automatic secret redaction.

## Supported Providers (12)

| Provider | Location | Output Folder |
|----------|----------|---------------|
| Claude Code | `~/.claude/projects/**/*.jsonl` | `claude-code-sessions/` |
| Codex CLI | `~/.codex/sessions/**/*.jsonl` | `codex-sessions/` |
| Cursor | `~/.cursor/projects/**/agent-transcripts/*.txt` | `cursor-sessions/` |
| Aider | `~/.aider.chat.history.md` | `aider-sessions/` |
| Cline | VS Code globalStorage | `cline-sessions/` |
| Gemini CLI | `~/.gemini/` | `gemini-cli-sessions/` |
| Continue.dev | `~/.continue/sessions/` | `continue-sessions/` |
| GitHub Copilot | VS Code globalStorage | `copilot-chat-sessions/` |
| Roo Code | VS Code globalStorage | `roo-code-sessions/` |
| Windsurf | Codeium/Windsurf app data | `windsurf-sessions/` |
| Zed AI | `~/.config/zed/conversations/` | `zed-ai-sessions/` |
| Amp (Sourcegraph) | VS Code globalStorage | `amp-sessions/` |

## CLI Commands

After installation, use the `aisync` command:

```bash
# Check status
aisync status

# Run sync now
aisync sync

# Set sync interval (in minutes)
aisync interval 5     # Every 5 minutes
aisync interval 15    # Every 15 minutes (default)
aisync interval 30    # Every 30 minutes

# List all providers
aisync providers

# View recent logs
aisync logs

# Enable/disable background sync
aisync enable
aisync disable

# Show help
aisync help
```

## Installation

Run the installer:

```bash
cd ~/.claude/skills/aisync/scripts
./install.sh
```

This will:
1. Copy all sync scripts to home directory
2. Install the `aisync` CLI
3. Set up automatic syncing (platform-specific)
4. Run initial sync

## Cross-Platform Support

| Platform | Scheduler | Auto-Install |
|----------|-----------|--------------|
| macOS | launchd | ✅ Automatic |
| Linux | systemd/cron | ✅ Automatic |
| Windows | Task Scheduler | 📋 Manual (instructions provided) |

## Manual Sync

```bash
# Sync all providers
python3 ~/sync_ai_sessions_to_obsidian.py

# Or use CLI
aisync sync
```

## Vault Configuration

The sync auto-detects your Obsidian vault. To specify manually:

```bash
# Option 1: Environment variable
export OBSIDIAN_VAULT="/path/to/your/vault"

# Option 2: Config file
echo 'OBSIDIAN_VAULT="/path/to/your/vault"' > ~/.aisync.conf
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No sessions found | Check if AI tools are installed and have sessions |
| Sync not running | Run `aisync status` to check |
| Permission errors | Run `chmod +x ~/sync_*.py` |
| Vault not found | Set `OBSIDIAN_VAULT` env var or create `~/.aisync.conf` |

## Scripts

The skill includes these scripts in `scripts/`:

- `aisync` - CLI management tool
- `sync_ai_sessions_to_obsidian.py` - Main orchestrator
- `sync_claude_code_to_obsidian.py` - Claude Code
- `sync_codex_to_obsidian.py` - Codex CLI
- `sync_cursor_to_obsidian.py` - Cursor
- `sync_aider_to_obsidian.py` - Aider
- `sync_cline_to_obsidian.py` - Cline
- `sync_gemini_cli_to_obsidian.py` - Gemini CLI
- `sync_continue_to_obsidian.py` - Continue.dev
- `sync_copilot_chat_to_obsidian.py` - GitHub Copilot
- `sync_roo_code_to_obsidian.py` - Roo Code
- `sync_windsurf_to_obsidian.py` - Windsurf
- `sync_zed_ai_to_obsidian.py` - Zed AI
- `sync_amp_to_obsidian.py` - Amp (Sourcegraph)
- `common.py` - Shared utilities
- `install.sh` - Cross-platform installer
