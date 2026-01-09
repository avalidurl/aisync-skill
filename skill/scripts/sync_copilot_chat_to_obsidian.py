#!/usr/bin/env python3
"""
Sync GitHub Copilot Chat sessions to Obsidian as markdown notes.
Copilot Chat stores data in VS Code's globalStorage:
- macOS: ~/Library/Application Support/Code/User/globalStorage/github.copilot-chat/
"""

import json
import os
import re
import platform
import sqlite3
from pathlib import Path
from datetime import datetime

# Paths
HOME = Path.home()
OBSIDIAN_VAULT = HOME / "Library/Mobile Documents/iCloud~md~obsidian/Documents/zettelkasten"
OUTPUT_DIR = OBSIDIAN_VAULT / "ai-sessions" / "copilot-chat-sessions"

def get_copilot_paths():
    """Get Copilot Chat storage paths for the current platform."""
    system = platform.system()
    paths = []
    
    if system == "Darwin":  # macOS
        paths.append(HOME / "Library/Application Support/Code/User/globalStorage/github.copilot-chat")
        paths.append(HOME / "Library/Application Support/Cursor/User/globalStorage/github.copilot-chat")
    elif system == "Linux":
        paths.append(HOME / ".config/Code/User/globalStorage/github.copilot-chat")
    elif system == "Windows":
        appdata = Path(os.environ.get('APPDATA', ''))
        paths.append(appdata / "Code/User/globalStorage/github.copilot-chat")
    
    return [p for p in paths if p.exists()]

# Secret patterns to redact
SECRET_PATTERNS = [
    (r'ghp_[a-zA-Z0-9]{36,}', '[REDACTED: GitHub PAT]'),
    (r'gho_[a-zA-Z0-9]{36,}', '[REDACTED: GitHub OAuth]'),
    (r'sk-[a-zA-Z0-9]{20,}', '[REDACTED: API Key]'),
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

def find_copilot_sessions(copilot_path):
    """Find Copilot Chat session data."""
    sessions = []
    
    # Check for chat sessions in various locations
    # Copilot Chat may store in SQLite DB or JSON files
    
    # Look for JSON session files
    for f in copilot_path.rglob("*.json"):
        if 'chat' in f.name.lower() or 'session' in f.name.lower() or 'conversation' in f.name.lower():
            sessions.append(('json', f))
    
    # Look for SQLite databases
    for f in copilot_path.rglob("*.db"):
        sessions.append(('sqlite', f))
    for f in copilot_path.rglob("*.vscdb"):
        sessions.append(('vscdb', f))
    
    # Check emptyWindowChatSessions if it exists
    chat_sessions = copilot_path.parent / "emptyWindowChatSessions"
    if chat_sessions.exists():
        for f in chat_sessions.rglob("*.json"):
            sessions.append(('json', f))
    
    return sessions

def parse_json_session(file_path):
    """Parse a JSON session file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return None
    
    messages = []
    
    # Handle different possible structures
    conversations = data if isinstance(data, list) else data.get('conversations', data.get('messages', [data]))
    
    for conv in conversations:
        if isinstance(conv, dict):
            # Extract messages from conversation
            msgs = conv.get('messages', conv.get('history', []))
            for msg in msgs:
                if isinstance(msg, dict):
                    role = msg.get('role', msg.get('author', 'unknown'))
                    content = msg.get('content', msg.get('text', msg.get('message', '')))
                    if content:
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
    """Convert a Copilot Chat session to markdown format."""
    messages = session.get('messages', [])
    if not messages:
        return None
    
    date = session.get('date', 'unknown')
    time = session.get('time', '00:00')
    session_id = session.get('session_id', 'unknown')
    
    # Get first user message as summary
    first_user = next((m['content'][:80] for m in messages if m['role'] == 'user'), 'Session')
    first_user = first_user.replace('\n', ' ').replace('"', '\\"').strip()
    
    frontmatter = f'''---
type: copilot-chat-session
date: {date}
time: "{time}"
session_id: "{session_id}"
tags:
  - copilot
  - github
  - ai-session
  - coding
summary: "{first_user}..."
---
'''

    content = f'''# 🐙 Copilot Chat Session — {date} {time.replace(':', '')}

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
            content += f"## 🐙 Copilot\n\n{text}\n\n---\n\n"
    
    content += "\n---\n*Session exported from GitHub Copilot Chat — secrets redacted*\n"
    
    return frontmatter + content

def main():
    """Main sync function."""
    print("🔄 Syncing GitHub Copilot Chat sessions to Obsidian...")
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Find Copilot storage paths
    copilot_paths = get_copilot_paths()
    
    if not copilot_paths:
        print("📁 No GitHub Copilot Chat directory found")
        return
    
    print(f"📁 Found {len(copilot_paths)} Copilot storage location(s)")
    
    synced = 0
    skipped = 0
    
    for copilot_path in copilot_paths:
        print(f"   Scanning: {copilot_path}")
        
        session_files = find_copilot_sessions(copilot_path)
        
        for file_type, session_file in session_files:
            if file_type == 'json':
                session = parse_json_session(session_file)
                if not session:
                    skipped += 1
                    continue
                
                markdown = session_to_markdown(session)
                if not markdown:
                    skipped += 1
                    continue
                
                # Generate filename
                date = session.get('date', 'unknown')
                time = session.get('time', '0000').replace(':', '')
                session_id = session.get('session_id', 'unknown')
                
                filename = f"copilot-chat-{date}-{time}-{session_id}.md"
                output_path = OUTPUT_DIR / filename
                
                # Check if already synced
                if output_path.exists():
                    source_mtime = Path(session['source_file']).stat().st_mtime
                    output_mtime = output_path.stat().st_mtime
                    if source_mtime <= output_mtime:
                        skipped += 1
                        continue
                
                # Write file
                output_path.write_text(markdown, encoding='utf-8')
                synced += 1
                print(f"  ✅ {filename}")
            else:
                # SQLite/VSCDB - skip for now (complex format)
                skipped += 1
    
    print(f"\n✅ Synced {synced} new sessions ({skipped} skipped)")
    print(f"📂 Output: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
