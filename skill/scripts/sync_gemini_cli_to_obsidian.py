#!/usr/bin/env python3
"""
Sync Gemini CLI sessions to Obsidian as markdown notes.
Gemini CLI stores data in ~/.gemini/
Note: Gemini CLI session format may vary - this handles known patterns.
"""

import json
import os
import re
from pathlib import Path
from datetime import datetime

# Paths
HOME = Path.home()
GEMINI_DIR = HOME / ".gemini"
OBSIDIAN_VAULT = HOME / "Library/Mobile Documents/iCloud~md~obsidian/Documents/zettelkasten"
OUTPUT_DIR = OBSIDIAN_VAULT / "ai-sessions" / "gemini-cli-sessions"

# Secret patterns to redact
SECRET_PATTERNS = [
    (r'AIza[a-zA-Z0-9_-]{35}', '[REDACTED: Google API Key]'),
    (r'ya29\.[a-zA-Z0-9_-]+', '[REDACTED: Google OAuth Token]'),
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

def find_gemini_sessions():
    """Find Gemini CLI session files."""
    sessions = []
    
    if not GEMINI_DIR.exists():
        return sessions
    
    # Look for session files in various possible locations
    possible_paths = [
        GEMINI_DIR / "sessions",
        GEMINI_DIR / "history",
        GEMINI_DIR / "chats",
        GEMINI_DIR / "conversations",
    ]
    
    for path in possible_paths:
        if path.exists():
            for f in path.rglob("*.json"):
                sessions.append(f)
            for f in path.rglob("*.jsonl"):
                sessions.append(f)
    
    # Also check for history files in main gemini dir
    for f in GEMINI_DIR.glob("*history*.json"):
        sessions.append(f)
    for f in GEMINI_DIR.glob("*session*.json"):
        sessions.append(f)
    
    return sessions

def parse_gemini_session(file_path):
    """Parse a Gemini CLI session file."""
    try:
        content = file_path.read_text(encoding='utf-8')
    except:
        return None
    
    messages = []
    
    # Try JSON format
    try:
        data = json.loads(content)
        
        # Handle different possible structures
        if isinstance(data, list):
            for entry in data:
                if isinstance(entry, dict):
                    role = entry.get('role', entry.get('author', 'unknown'))
                    text = entry.get('content', entry.get('text', entry.get('message', '')))
                    if text:
                        messages.append({
                            'role': 'user' if role in ['user', 'human'] else 'assistant',
                            'content': str(text)
                        })
        elif isinstance(data, dict):
            # Single session object
            history = data.get('history', data.get('messages', data.get('conversation', [])))
            for entry in history:
                if isinstance(entry, dict):
                    role = entry.get('role', entry.get('author', 'unknown'))
                    text = entry.get('content', entry.get('text', entry.get('message', '')))
                    if text:
                        messages.append({
                            'role': 'user' if role in ['user', 'human'] else 'assistant',
                            'content': str(text)
                        })
    except json.JSONDecodeError:
        # Try JSONL format
        for line in content.split('\n'):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                role = entry.get('role', entry.get('author', 'unknown'))
                text = entry.get('content', entry.get('text', entry.get('message', '')))
                if text:
                    messages.append({
                        'role': 'user' if role in ['user', 'human'] else 'assistant',
                        'content': str(text)
                    })
            except:
                continue
    
    if not messages:
        return None
    
    # Get file modification time
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
    """Convert a Gemini session to markdown format."""
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
type: gemini-cli-session
date: {date}
time: "{time}"
session_id: "{session_id}"
tags:
  - gemini
  - google
  - ai-session
  - coding
summary: "{first_user}..."
---
'''

    content = f'''# 💎 Gemini CLI Session — {date} {time.replace(':', '')}

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
            content += f"## 💎 Gemini\n\n{text}\n\n---\n\n"
    
    content += "\n---\n*Session exported from Gemini CLI — secrets redacted*\n"
    
    return frontmatter + content

def main():
    """Main sync function."""
    print("🔄 Syncing Gemini CLI sessions to Obsidian...")
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    if not GEMINI_DIR.exists():
        print(f"📁 Gemini CLI directory not found: {GEMINI_DIR}")
        return
    
    # Find session files
    session_files = find_gemini_sessions()
    
    if not session_files:
        print(f"📁 No Gemini session files found in {GEMINI_DIR}")
        print("   Gemini CLI may not have created any sessions yet")
        return
    
    print(f"📁 Found {len(session_files)} session file(s)")
    
    synced = 0
    skipped = 0
    
    for session_file in session_files:
        session = parse_gemini_session(session_file)
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
        
        filename = f"gemini-cli-{date}-{time}-{session_id}.md"
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
    
    print(f"\n✅ Synced {synced} new sessions ({skipped} skipped)")
    print(f"📂 Output: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
