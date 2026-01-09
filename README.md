# aisync

**Automatically sync AI coding sessions to Obsidian**

A skill that backs up your AI coding sessions to an Obsidian vault as searchable markdown notes — with automatic secret redaction. Supports **12 AI coding agents**.

![License](https://img.shields.io/badge/license-Unlicense-blue.svg)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![Providers](https://img.shields.io/badge/providers-12-blue.svg)

## Features

- 🔄 **Automatic syncing** via macOS launchd (configurable interval)
- 🔒 **Secret redaction** - API keys, tokens, passwords automatically removed
- 📁 **Organized output** - Sessions sorted by tool and date
- 🔍 **Searchable** - Full markdown with frontmatter for Obsidian queries
- ⚡ **Lightweight** - Minimal resource usage, runs in background
- 🎮 **CLI management** - Easy commands to control sync

## Supported AI Tools (12)

| Tool | Session Location | Output Folder |
|------|-----------------|---------------|
| **Claude Code** | `~/.claude/projects/**/*.jsonl` | `claude-code-sessions/` |
| **Codex CLI** | `~/.codex/sessions/**/*.jsonl` | `codex-sessions/` |
| **Cursor** | `~/.cursor/projects/**/agent-transcripts/*.txt` | `cursor-sessions/` |
| **Aider** | `~/.aider.chat.history.md` | `aider-sessions/` |
| **Cline** | VS Code globalStorage | `cline-sessions/` |
| **Gemini CLI** | `~/.gemini/` | `gemini-cli-sessions/` |
| **Continue.dev** | `~/.continue/sessions/` | `continue-sessions/` |
| **GitHub Copilot** | VS Code globalStorage | `copilot-chat-sessions/` |
| **Roo Code** | VS Code globalStorage | `roo-code-sessions/` |
| **Windsurf** | `~/Library/App Support/Windsurf` | `windsurf-sessions/` |
| **Zed AI** | `~/.config/zed/conversations/` | `zed-ai-sessions/` |
| **Amp (Sourcegraph)** | VS Code globalStorage | `amp-sessions/` |

## Installation

### Quick Install

```bash
# Clone the repo
git clone https://github.com/avalidurl/aisync-skill.git
cd aisync-skill

# Run the installer
./skill/scripts/install.sh
```

This will:
1. Copy all sync scripts to your home directory
2. Install the `aisync` CLI tool
3. Create a launchd agent for automatic syncing
4. Start syncing every 15 minutes
5. Run an initial sync immediately

## CLI Commands

After installation, use the `aisync` command:

```bash
# Check status
aisync status

# Run sync now
aisync sync

# Set sync interval (in minutes)
aisync interval 5     # Every 5 minutes
aisync interval 30    # Every 30 minutes
aisync interval 60    # Every hour

# List all providers
aisync providers

# View recent logs
aisync logs
aisync logs 50        # Last 50 entries

# Enable/disable background sync
aisync enable
aisync disable

# Show help
aisync help
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

Use the CLI to change the interval:

```bash
aisync interval 5    # Sync every 5 minutes
aisync interval 15   # Sync every 15 minutes (default)
aisync interval 60   # Sync every hour
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

- API keys (OpenAI, Anthropic, GitHub, AWS, Google, Sourcegraph, etc.)
- Bearer tokens and JWTs
- OAuth tokens
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

- **macOS, Linux, or Windows**
- Python 3.8+
- Obsidian with a vault configured

## Cross-Platform Support

| Platform | Scheduler | Auto-Install |
|----------|-----------|--------------|
| **macOS** | launchd | ✅ Automatic |
| **Linux** | systemd/cron | ✅ Automatic |
| **Windows** | Task Scheduler | 📋 Manual (see install output) |
| **WSL** | systemd/cron | ✅ Automatic |

### Obsidian Vault Detection

The sync scripts auto-detect your Obsidian vault. To specify manually:

```bash
# Option 1: Environment variable
export OBSIDIAN_VAULT="/path/to/your/vault"

# Option 2: Config file
echo 'OBSIDIAN_VAULT="/path/to/your/vault"' > ~/.aisync.conf
```

## Not Supported (Cloud-Only)

These tools don't store sessions locally and cannot be synced:
- **Devin** - Runs entirely in cloud IDE
- **Replit Agent** - Cloud-based
- **v0.dev / bolt.new** - Web-based

## License

**Public Domain (Unlicense)** - No copyright. Do whatever you want with it. See [LICENSE](LICENSE).

## Contributing

Contributions welcome! Please open an issue or PR.

### Adding a New Provider

1. Create `sync_<provider>_to_obsidian.py` based on existing scripts
2. Add to `OPTIONAL_SCRIPTS` in `sync_ai_sessions_to_obsidian.py`
3. Add to `PROVIDERS` list in `aisync` CLI
4. Update `install.sh` to copy the new script
5. Update this README
