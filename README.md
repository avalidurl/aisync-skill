# aisync

**Automatically sync AI coding sessions to Obsidian**

A skill that backs up your Claude Code, Codex CLI, and Cursor chat sessions to an Obsidian vault as searchable markdown notes — with automatic secret redaction.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Platform](https://img.shields.io/badge/platform-macOS-lightgrey.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)

## Features

- 🔄 **Automatic syncing** every 15 minutes via macOS launchd
- 🔒 **Secret redaction** - API keys, tokens, passwords automatically removed
- 📁 **Organized output** - Sessions sorted by tool and date
- 🔍 **Searchable** - Full markdown with frontmatter for Obsidian queries
- ⚡ **Lightweight** - Minimal resource usage, runs in background

## Supported Sources

| Tool | Session Location | Output |
|------|-----------------|--------|
| Claude Code | `~/.claude/projects/**/*.jsonl` | `ai-sessions/claude-code-sessions/` |
| Codex CLI | `~/.codex/sessions/**/*.jsonl` | `ai-sessions/codex-sessions/` |
| Cursor | `~/.cursor/projects/**/agent-transcripts/*.txt` | `ai-sessions/cursor-sessions/` |

## Installation

### Quick Install

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/aisync-skill.git
cd aisync-skill

# Run the installer
./skill/scripts/install.sh
```

This will:
1. Copy sync scripts to your home directory
2. Create a launchd agent for automatic syncing
3. Start syncing every 15 minutes
4. Run an initial sync immediately

### Manual Install

```bash
# Copy scripts
cp skill/scripts/sync_*.py ~/

# Make executable
chmod +x ~/sync_*.py

# Run manually
python3 ~/sync_ai_sessions_to_obsidian.py
```

## Configuration

### Obsidian Vault Path

By default, scripts look for your vault at:
```
~/Library/Mobile Documents/iCloud~md~obsidian/Documents/zettelkasten
```

To change this, edit the `OBSIDIAN_VAULT` variable in each sync script:

```python
OBSIDIAN_VAULT = Path.home() / "path/to/your/vault"
```

### Sync Interval

Default is 15 minutes (900 seconds). To change, edit the plist:

```bash
# Open the plist
nano ~/Library/LaunchAgents/com.$(whoami).ai-sessions-sync.plist

# Change StartInterval value (in seconds)
# 300 = 5 min, 900 = 15 min, 1800 = 30 min, 3600 = 1 hour
```

Then reload:
```bash
launchctl unload ~/Library/LaunchAgents/com.$(whoami).ai-sessions-sync.plist
launchctl load ~/Library/LaunchAgents/com.$(whoami).ai-sessions-sync.plist
```

## Usage

### Manual Sync

```bash
# Sync all sources
python3 ~/sync_ai_sessions_to_obsidian.py

# Sync individual sources
python3 ~/sync_claude_code_to_obsidian.py
python3 ~/sync_codex_to_obsidian.py
python3 ~/sync_cursor_to_obsidian.py
```

### Check Status

```bash
# Is auto-sync running?
launchctl list | grep ai-sessions-sync

# View sync log
cat ~/.ai-sessions-sync.log

# View detailed output
tail -f ~/.ai-sessions-sync-stdout.log
```

### Stop/Start Auto-Sync

```bash
# Stop
launchctl unload ~/Library/LaunchAgents/com.$(whoami).ai-sessions-sync.plist

# Start
launchctl load ~/Library/LaunchAgents/com.$(whoami).ai-sessions-sync.plist
```

## Output Format

Each session is saved as a markdown file with YAML frontmatter:

```markdown
---
type: claude-code-session
date: 2026-01-09
time: "14:30"
session_id: "abc12345"
working_dir: "/Users/you/project"
tags:
  - claude-code
  - ai-session
  - coding
---

# 🤖 Claude Code Session — 2026-01-09 1430

## 👤 User

How do I fix this bug?

---

## 🤖 Claude

Here's how to fix it...
```

## Security

All sync scripts automatically redact:

- API keys (OpenAI, Anthropic, GitHub, AWS, etc.)
- Bearer tokens and JWTs
- Database connection strings
- Passwords and secrets in config files
- Private keys and certificates

## As a Claude/Codex Skill

To use as a skill, copy the `skill/` folder to your skills directory:

```bash
# For Claude
cp -r skill ~/.claude/skills/aisync

# For Codex
cp -r skill ~/.codex/skills/aisync
```

Then trigger with `@aisync` or `$aisync`.

## Requirements

- macOS (uses launchd for scheduling)
- Python 3.8+
- Obsidian with a vault configured

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! Please open an issue or PR.
