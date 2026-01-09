# aisync v2.2.0

**Sync AI coding sessions to Obsidian, JSON, HTML, or SQLite**

A modular library that backs up your AI coding sessions with analytics, search, and automatic secret redaction. Supports **14 AI coding agents** and **5 output formats**.

![License](https://img.shields.io/badge/license-Unlicense-blue.svg)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![Providers](https://img.shields.io/badge/providers-14-blue.svg)
![Outputs](https://img.shields.io/badge/outputs-5-green.svg)

## ✨ Features

- 🔄 **14 AI Tools** - Claude Code, Codex, Cursor, Aider, Cline, Gemini CLI, Continue, Copilot, Roo Code, Windsurf, Zed AI, Amp, OpenCode, OpenRouter
- 📤 **5 Outputs** - Obsidian, JSON, JSONL, HTML, SQLite
- 🔒 **Secret Redaction** - 20+ patterns (API keys, tokens, passwords)
- 📊 **Analytics** - Token usage, language detection, activity patterns
- 🔍 **Search** - Full-text search with regex support
- ⚡ **Cross-Platform** - macOS, Linux, Windows

## 🚀 Quick Start

```bash
# Install
git clone https://github.com/avalidurl/aisync-skill.git
cd aisync-skill && ./skill/scripts/install.sh

# Sync to Obsidian
aisync sync

# Sync to multiple formats
aisync sync -f obsidian json html

# Search sessions
aisync search "async function"

# View statistics
aisync stats
```

## 📋 CLI Commands

```
🤖 AI Sessions Sync v2.2.0

COMMANDS:
  sync       Sync sessions to output format(s)
  search     Search across all sessions  
  stats      Show usage statistics
  report     Generate detailed report
  status     Show detected sessions
  providers  List supported AI tools
  outputs    List output formats
  config     Get/set configuration
```

### Sync Command

```bash
aisync sync                          # Sync to Obsidian (default)
aisync sync -o ~/ai-sessions         # Custom output directory
aisync sync -f obsidian json html    # Multiple output formats
aisync sync -p claude-code cursor    # Only specific providers
aisync sync -f sqlite --no-analyze   # SQLite without analytics
```

### Search Command

```bash
aisync search "async function"       # Simple search
aisync search "error" -p cursor      # Filter by provider
aisync search "def \w+\(" --regex    # Regex search
aisync search "api" --json -l 50     # JSON output
```

### Stats & Report

```bash
aisync stats                 # Human-readable stats
aisync stats -f json         # JSON for scripting
aisync report                # Detailed report
aisync report -o ~/report.txt
```

## 🔧 Supported AI Tools (14)

| Tool | Session Location | Status |
|------|------------------|--------|
| **Claude Code** | `~/.claude/projects/**/*.jsonl` | ✅ |
| **Codex CLI** | `~/.codex/sessions/**/*.jsonl` | ✅ |
| **Cursor** | Cursor globalStorage | ✅ |
| **Aider** | `~/.aider.chat.history.md` | ✅ |
| **Cline** | VS Code globalStorage | ✅ |
| **Gemini CLI** | `~/.gemini/` | ✅ |
| **Continue.dev** | `~/.continue/sessions/` | ✅ |
| **GitHub Copilot** | VS Code globalStorage | ✅ |
| **Roo Code** | VS Code globalStorage | ✅ |
| **Windsurf** | Windsurf app data | ✅ |
| **Zed AI** | `~/.config/zed/conversations/` | ✅ |
| **Amp (Sourcegraph)** | VS Code globalStorage | ✅ |
| **OpenCode** | `~/.local/share/opencode/` | ✅ |
| **OpenRouter** | `~/Downloads/openrouter*.json` | ✅ |

## 📤 Output Formats (5)

| Format | Description | Use Case |
|--------|-------------|----------|
| `obsidian` | Markdown + YAML frontmatter | Knowledge base |
| `json` | JSON files | API/scripting |
| `jsonl` | JSON Lines | Streaming/ETL |
| `html` | Static website | Browsing/sharing |
| `sqlite` | SQLite database | Querying/analysis |

## 📊 Analytics

The analytics module provides:

- **Token estimation** - Approximate token usage per session
- **Language detection** - Programming languages in code blocks
- **Activity patterns** - Peak hours, day-of-week distribution
- **Streaks** - Consecutive coding days
- **Insights** - Productivity patterns, tool preferences

```bash
aisync stats

📊 AI Sessions Statistics
========================================
Total sessions:  78
Total messages:  1,234
Total tokens:    456,789
Code blocks:     567

By Provider:
  claude-code: 65
  codex: 13

Top Languages:
  python: 234
  javascript: 156
  typescript: 89
```

## 🔍 Search

Full-text search across all sessions:

```python
from aisync import SessionSearch, SearchOptions

search = SessionSearch(sessions)

# Simple search
results = search.search_simple("async function")

# Advanced search
options = SearchOptions(
    query="error handling",
    provider="cursor",
    limit=20,
    regex=True
)
results = search.search(options)
```

## 🔒 Security

Automatic redaction of 20+ secret patterns:

- API keys (OpenAI, Anthropic, GitHub, AWS, Google)
- Bearer tokens, JWTs
- Database connection strings
- Private keys, SSH keys
- Passwords in URLs
- Webhook URLs

## ⚙️ Configuration

```bash
# Environment variable
export OBSIDIAN_VAULT="/path/to/vault"

# Config file (~/.aisync.conf)
OBSIDIAN_VAULT="/path/to/vault"
DEFAULT_OUTPUT="obsidian"
REDACT_SECRETS="true"

# CLI
aisync config OBSIDIAN_VAULT "~/Documents/Obsidian/MyVault"
```

## 🖥️ Cross-Platform

| Platform | Scheduler | Auto-Install |
|----------|-----------|--------------|
| **macOS** | launchd | ✅ Automatic |
| **Linux** | systemd/cron | ✅ Automatic |
| **Windows** | Task Scheduler | 📋 Manual |

## 📁 Project Structure

```
skill/
├── SKILL.md           # Skill definition
├── lib/               # Python library
│   ├── __init__.py    # Main API
│   ├── cli.py         # CLI
│   ├── models.py      # Data models
│   ├── redact.py      # Secret redaction
│   ├── search.py      # Search
│   ├── parsers/       # 14 provider parsers
│   ├── outputs/       # 5 output plugins
│   └── analytics/     # Analytics & insights
└── scripts/
    └── install.sh     # Cross-platform installer
```

## 📝 As a Skill

Copy to your skills directory:

```bash
# For Claude Code
cp -r skill ~/.claude/skills/aisync

# For Codex CLI
cp -r skill ~/.codex/skills/aisync
```

## 🚫 Not Supported (Cloud-Only)

These tools don't store sessions locally:
- **Devin** - Cloud IDE
- **Replit Agent** - Cloud-based
- **v0.dev / bolt.new** - Web-based

## 📄 License

**Public Domain (Unlicense)** - Do whatever you want with it.

## 🤝 Contributing

Contributions welcome! See `skill/lib/parsers/` for examples of adding new providers.
