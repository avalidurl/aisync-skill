#!/usr/bin/env python3
"""
Sync Sourcegraph Amp sessions to Obsidian as markdown notes.
Amp stores data in VS Code's globalStorage:
- macOS: ~/Library/Application Support/Code/User/globalStorage/sourcegraph.cody-ai/
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
OUTPUT_DIR = OBSIDIAN_VAULT / "ai-sessions" / "amp-sessions"

def get_amp_paths():
    """Get Sourcegraph Amp/Cody storage paths."""
    system = platform.system()
    paths = []
    
    if system == "Darwin":  # macOS
        # Amp uses cody-ai extension under the hood
        paths.append(HOME / "Library/Application Support/Code/User/globalStorage/sourcegraph.cody-ai")
        paths.append(HOME / "Library/Application Support/Cursor/User/globalStorage/sourcegraph.cody-ai")
    elif system == "Linux":
        paths.append(HOME / ".config/Code/User/globalStorage/sourcegraph.cody-ai")
    elif system == "Windows":
        appdata = Path(os.environ.get('APPDATA', ''))
        paths.append(appdata / "Code/User/globalStorage/sourcegraph.cody-ai")
    
    return [p for p in paths if p.exists()]

# Secret patterns to redact
SECRET_PATTERNS = [
    (r'sgp_[a-zA-Z0-9_-]{40,}', '[REDACTED: Sourcegraph Token]'),
    (r'sk-[a-zA-Z0-9]{20,}', '[REDACTED: API Key]'),
    (r'sk-ant-[a-zA-Z0-9-]{20,}', '[REDACTED: Anthropic API Key]'),
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

def find_amp_sessions(amp_path):
    """Find Amp/Cody session files."""
    sessions = []
    
    # Look for chat history files
    possible_locations = [
        amp_path / "chat",
        amp_path / "chats",
        amp_path / "conversations",
        amp_path / "history",
    ]
    
    for location in possible_locations:
        if location.exists():
            for f in location.rglob("*.json"):
                sessions.append(f)
    
    # Also check main directory for chat files
    for f in amp_path.glob("*chat*.json"):
        sessions.append(f)
    for f in amp_path.glob("*history*.json"):
        sessions.append(f)
    
    return list(set(sessions))

def parse_amp_session(file_path):
    """Parse an Amp/Cody session file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return None
    
    messages = []
    
    # Handle different structures
    if isinstance(data, dict):
        history = data.get('messages', data.get('history', data.get('chat', [])))
        if isinstance(history, dict):
            history = history.get('messages', [])
    elif isinstance(data, list):
        history = data
    else:
        return None
    
    for entry in history:
        if isinstance(entry, dict):
            role = entry.get('role', entry.get('speaker', entry.get('author', 'unknown')))
            content = entry.get('content', entry.get('text', entry.get('message', '')))
            
            # Handle displayText vs content
            if not content and entry.get('displayText'):
                content = entry['displayText']
            
            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and item.get('type') == 'text':
                        text_parts.append(item.get('text', ''))
                    elif isinstance(item, str):
                        text_parts.append(item)
                content = '\n'.join(text_parts)
            
            if content and len(str(content).strip()) > 5:
                # Normalize role
                role_lower = str(role).lower()
                is_user = role_lower in ['user', 'human', 'you']
                messages.append({
                    'role': 'user' if is_user else 'assistant',
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
    """Convert an Amp session to markdown format."""
    messages = session.get('messages', [])
    if not messages:
        return None
    
    date = session.get('date', 'unknown')
    time = session.get('time', '00:00')
    session_id = session.get('session_id', 'unknown')
    
    first_user = next((m['content'][:80] for m in messages if m['role'] == 'user'), 'Session')
    first_user = first_user.replace('\n', ' ').replace('"', '\\"').strip()
    
    frontmatter = f'''---
type: amp-session
date: {date}
time: "{time}"
session_id: "{session_id}"
tags:
  - amp
  - sourcegraph
  - cody
  - ai-session
  - coding
summary: "{first_user}..."
---
'''

    content = f'''# ⚡ Amp Session — {date} {time.replace(':', '')}

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
            content += f"## ⚡ Amp\n\n{text}\n\n---\n\n"
    
    content += "\n---\n*Session exported from Sourcegraph Amp — secrets redacted*\n"
    
    return frontmatter + content

def main():
    """Main sync function."""
    print("🔄 Syncing Sourcegraph Amp sessions to Obsidian...")
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    amp_paths = get_amp_paths()
    
    if not amp_paths:
        print("📁 No Sourcegraph Amp/Cody directory found")
        return
    
    print(f"📁 Found {len(amp_paths)} Amp storage location(s)")
    
    synced = 0
    skipped = 0
    
    for amp_path in amp_paths:
        print(f"   Scanning: {amp_path}")
        
        session_files = find_amp_sessions(amp_path)
        
        for session_file in session_files:
            session = parse_amp_session(session_file)
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
            
            filename = f"amp-{date}-{time}-{session_id}.md"
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
