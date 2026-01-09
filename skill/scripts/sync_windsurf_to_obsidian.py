#!/usr/bin/env python3
"""
Sync Windsurf (Codeium) sessions to Obsidian as markdown notes.
Windsurf stores data in:
- macOS: ~/Library/Application Support/Windsurf/
- Linux: ~/.config/Windsurf/
- Windows: %APPDATA%/Windsurf/
"""

import json
import os
import re
import platform
from pathlib import Path
from datetime import datetime

# Paths
HOME = Path.home()
OBSIDIAN_VAULT = HOME / "Library/Mobile Documents/iCloud~md~obsidian/Documents/zettelkasten"
OUTPUT_DIR = OBSIDIAN_VAULT / "ai-sessions" / "windsurf-sessions"

def get_windsurf_paths():
    """Get Windsurf storage paths for the current platform."""
    system = platform.system()
    paths = []
    
    if system == "Darwin":  # macOS
        paths.append(HOME / "Library/Application Support/Windsurf")
        paths.append(HOME / "Library/Application Support/Codeium")
    elif system == "Linux":
        paths.append(HOME / ".config/Windsurf")
        paths.append(HOME / ".config/Codeium")
    elif system == "Windows":
        appdata = Path(os.environ.get('APPDATA', ''))
        paths.append(appdata / "Windsurf")
        paths.append(appdata / "Codeium")
    
    return [p for p in paths if p.exists()]

# Secret patterns to redact
SECRET_PATTERNS = [
    (r'sk-[a-zA-Z0-9]{20,}', '[REDACTED: API Key]'),
    (r'ghp_[a-zA-Z0-9]{36,}', '[REDACTED: GitHub PAT]'),
    (r'Bearer\s+[a-zA-Z0-9._-]{20,}', '[REDACTED: Bearer Token]'),
    (r'eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*', '[REDACTED: JWT Token]'),
]

def redact_secrets(text):
    """Redact sensitive information from text."""
    if not text:
        return text
    for pattern, replacement in SECRET_PATTERNS:
        text = re.sub(pattern, replacement, text)
    return text

def find_windsurf_sessions(windsurf_path):
    """Find Windsurf session files."""
    sessions = []
    
    # Look for chat/conversation files
    possible_dirs = [
        windsurf_path / "User" / "History",
        windsurf_path / "User" / "globalStorage",
        windsurf_path / "chats",
        windsurf_path / "conversations",
    ]
    
    for search_dir in possible_dirs:
        if search_dir.exists():
            for f in search_dir.rglob("*.json"):
                sessions.append(f)
    
    return sessions

def parse_windsurf_session(file_path):
    """Parse a Windsurf session file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return None
    
    messages = []
    
    # Handle different possible structures
    if isinstance(data, dict):
        history = data.get('messages', data.get('history', data.get('conversation', [])))
    elif isinstance(data, list):
        history = data
    else:
        return None
    
    for entry in history:
        if isinstance(entry, dict):
            role = entry.get('role', entry.get('author', 'unknown'))
            content = entry.get('content', entry.get('text', entry.get('message', '')))
            
            if isinstance(content, list):
                text_parts = [item.get('text', str(item)) if isinstance(item, dict) else str(item) for item in content]
                content = '\n'.join(text_parts)
            
            if content and len(str(content).strip()) > 10:
                messages.append({
                    'role': 'user' if role in ['user', 'human'] else 'assistant',
                    'content': str(content)
                })
    
    if not messages:
        return None
    
    mtime = file_path.stat().st_mtime
    dt = datetime.fromtimestamp(mtime)
    
    return {
        'session_id': file_path.stem[:8],
        'date': dt.strftime('%Y-%m-%d'),
        'time': dt.strftime('%H:%M'),
        'messages': messages,
        'source_file': str(file_path)
    }

def session_to_markdown(session):
    """Convert a Windsurf session to markdown format."""
    messages = session.get('messages', [])
    if not messages:
        return None
    
    date = session.get('date', 'unknown')
    time = session.get('time', '00:00')
    session_id = session.get('session_id', 'unknown')
    
    first_user = next((m['content'][:80] for m in messages if m['role'] == 'user'), 'Session')
    first_user = first_user.replace('\n', ' ').replace('"', '\\"').strip()
    
    frontmatter = f'''---
type: windsurf-session
date: {date}
time: "{time}"
session_id: "{session_id}"
tags:
  - windsurf
  - codeium
  - ai-session
  - coding
summary: "{first_user}..."
---
'''

    content = f'''# 🏄 Windsurf Session — {date} {time.replace(':', '')}

| Property | Value |
|----------|-------|
| **Date** | {date} {time} |
| **Session ID** | `{session_id}` |

---

'''

    for msg in messages:
        text = redact_secrets(msg['content'])
        if msg['role'] == 'user':
            content += f"## 👤 User\n\n{text}\n\n---\n\n"
        else:
            content += f"## 🏄 Windsurf\n\n{text}\n\n---\n\n"
    
    content += "\n---\n*Session exported from Windsurf (Codeium) — secrets redacted*\n"
    
    return frontmatter + content

def main():
    """Main sync function."""
    print("🔄 Syncing Windsurf sessions to Obsidian...")
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    windsurf_paths = get_windsurf_paths()
    
    if not windsurf_paths:
        print("📁 No Windsurf/Codeium directory found")
        return
    
    print(f"📁 Found {len(windsurf_paths)} Windsurf storage location(s)")
    
    synced = 0
    skipped = 0
    
    for windsurf_path in windsurf_paths:
        print(f"   Scanning: {windsurf_path}")
        
        session_files = find_windsurf_sessions(windsurf_path)
        
        for session_file in session_files:
            session = parse_windsurf_session(session_file)
            if not session:
                skipped += 1
                continue
            
            markdown = session_to_markdown(session)
            if not markdown:
                skipped += 1
                continue
            
            date = session.get('date', 'unknown')
            time = session.get('time', '0000').replace(':', '')
            session_id = session.get('session_id', 'unknown')
            
            filename = f"windsurf-{date}-{time}-{session_id}.md"
            output_path = OUTPUT_DIR / filename
            
            if output_path.exists():
                source_mtime = Path(session['source_file']).stat().st_mtime
                output_mtime = output_path.stat().st_mtime
                if source_mtime <= output_mtime:
                    skipped += 1
                    continue
            
            output_path.write_text(markdown, encoding='utf-8')
            synced += 1
            print(f"  ✅ {filename}")
    
    print(f"\n✅ Synced {synced} new sessions ({skipped} skipped)")
    print(f"📂 Output: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
