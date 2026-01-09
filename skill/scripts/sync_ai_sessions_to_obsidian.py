#!/usr/bin/env python3
"""
Unified AI Sessions Sync to Obsidian
=====================================
Syncs AI coding sessions from multiple tools to Zettelkasten vault.
Runs automatically via launchd every 15 minutes.

Supported tools:
- Claude Code (Anthropic CLI)
- Codex CLI (OpenAI)
- Cursor IDE
- Aider (CLI agent)
- Cline (VS Code extension)
- Gemini CLI (Google)

Manual run: python3 ~/sync_ai_sessions_to_obsidian.py
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

HOME = Path.home()
LOG_FILE = HOME / ".ai-sessions-sync.log"

# Core providers (always run)
SYNC_SCRIPTS = [
    HOME / "sync_claude_code_to_obsidian.py",
    HOME / "sync_codex_to_obsidian.py", 
    HOME / "sync_cursor_to_obsidian.py",
]

# Additional providers (run if script exists)
OPTIONAL_SCRIPTS = [
    HOME / "sync_aider_to_obsidian.py",
    HOME / "sync_cline_to_obsidian.py",
    HOME / "sync_gemini_cli_to_obsidian.py",
    HOME / "sync_continue_to_obsidian.py",
    HOME / "sync_copilot_chat_to_obsidian.py",
    HOME / "sync_roo_code_to_obsidian.py",
    HOME / "sync_windsurf_to_obsidian.py",
    HOME / "sync_zed_ai_to_obsidian.py",
    HOME / "sync_amp_to_obsidian.py",
]

def log(message):
    """Log message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    
    # Append to log file (keep last 500 lines)
    try:
        lines = []
        if LOG_FILE.exists():
            lines = LOG_FILE.read_text().strip().split('\n')[-499:]
        lines.append(log_entry)
        LOG_FILE.write_text('\n'.join(lines) + '\n')
    except:
        pass

def run_sync(script_path):
    """Run a sync script and return success status."""
    if not script_path.exists():
        log(f"  ⚠️  Script not found: {script_path.name}")
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        # Extract summary line from output
        for line in result.stdout.strip().split('\n'):
            if '✅' in line and 'Synced' in line:
                log(f"  {line.strip()}")
                break
        
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        log(f"  ⚠️  Timeout: {script_path.name}")
        return False
    except Exception as e:
        log(f"  ❌ Error running {script_path.name}: {e}")
        return False

def main():
    log("🔄 Starting AI Sessions Sync...")
    
    # Combine core and optional scripts
    all_scripts = SYNC_SCRIPTS + [s for s in OPTIONAL_SCRIPTS if s.exists()]
    
    success_count = 0
    for script in all_scripts:
        name = script.stem.replace('sync_', '').replace('_to_obsidian', '').replace('_', ' ').title()
        log(f"  📂 {name}...")
        if run_sync(script):
            success_count += 1
    
    log(f"✅ Sync complete ({success_count}/{len(all_scripts)} providers)")

if __name__ == "__main__":
    main()
