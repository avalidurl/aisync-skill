#!/usr/bin/env python3
"""
Sync Continue.dev sessions to Obsidian as markdown notes.
Continue stores sessions in:
- ~/.continue/sessions/
"""

import json
import os
import re
from pathlib import Path
from datetime import datetime

# Paths
HOME = Path.home()
CONTINUE_DIR = HOME / ".continue"
OBSIDIAN_VAULT = HOME / "Library/Mobile Documents/iCloud~md~obsidian/Documents/zettelkasten"
OUTPUT_DIR = OBSIDIAN_VAULT / "ai-sessions" / "continue-sessions"

# Secret patterns to redact
SECRET_PATTERNS = [
    (r'sk-[a-zA-Z0-9]{20,}', '[REDACTED: OpenAI API Key]'),
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

def find_continue_sessions():
    """Find Continue.dev session files."""
    sessions_dir = CONTINUE_DIR / "sessions"
    
    if not sessions_dir.exists():
        return []
    
    session_files = []
    for f in sessions_dir.glob("*.json"):
        session_files.append(f)
    
    return session_files

def parse_continue_session(file_path):
    """Parse a Continue.dev session file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return None
    
    messages = []
    
    # Continue.dev session format varies but typically has history array
    history = data.get('history', data.get('messages', []))
    
    for entry in history:
        if isinstance(entry, dict):
            role = entry.get('role', 'unknown')
            content = entry.get('content', entry.get('message', ''))
            
            if isinstance(content, list):
                # Handle content array format
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and item.get('type') == 'text':
                        text_parts.append(item.get('text', ''))
                    elif isinstance(item, str):
                        text_parts.append(item)
                content = '\n'.join(text_parts)
            
            if content and len(str(content).strip()) > 5:
                messages.append({
                    'role': 'user' if role in ['user', 'human'] else 'assistant',
                    'content': str(content)
                })
    
    if not messages:
        return None
    
    # Get session metadata
    session_id = data.get('sessionId', file_path.stem[:8])
    model = data.get('model', data.get('selectedModelTitle', 'unknown'))
    
    # Get file modification time
    mtime = file_path.stat().st_mtime
    dt = datetime.fromtimestamp(mtime)
    
    return {
        'session_id': session_id[:8] if session_id else file_path.stem[:8],
        'date': dt.strftime('%Y-%m-%d'),
        'time': dt.strftime('%H:%M'),
        'model': model,
        'messages': messages,
        'source_file': str(file_path)
    }

def session_to_markdown(session):
    """Convert a Continue session to markdown format."""
    messages = session.get('messages', [])
    if not messages:
        return None
    
    date = session.get('date', 'unknown')
    time = session.get('time', '00:00')
    session_id = session.get('session_id', 'unknown')
    model = session.get('model', 'unknown')
    
    # Get first user message as summary
    first_user = next((m['content'][:80] for m in messages if m['role'] == 'user'), 'Session')
    first_user = first_user.replace('\n', ' ').replace('"', '\\"').strip()
    
    frontmatter = f'''---
type: continue-session
date: {date}
time: "{time}"
session_id: "{session_id}"
model: "{model}"
tags:
  - continue
  - ai-session
  - coding
summary: "{first_user}..."
---
'''

    content = f'''# 🔄 Continue Session — {date} {time.replace(':', '')}

| Property | Value |
|----------|-------|
| **Date** | {date} {time} |
| **Session ID** | `{session_id}` |
| **Model** | {model} |

---

'''

    for msg in messages:
        text = redact_secrets(msg['content'])
        if msg['role'] == 'user':
            content += f"## 👤 User\n\n{text}\n\n---\n\n"
        else:
            content += f"## 🤖 Continue\n\n{text}\n\n---\n\n"
    
    content += "\n---\n*Session exported from Continue.dev — secrets redacted*\n"
    
    return frontmatter + content

def main():
    """Main sync function."""
    print("🔄 Syncing Continue.dev sessions to Obsidian...")
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    if not CONTINUE_DIR.exists():
        print(f"📁 Continue.dev directory not found: {CONTINUE_DIR}")
        return
    
    # Find session files
    session_files = find_continue_sessions()
    
    if not session_files:
        print(f"📁 No Continue session files found in {CONTINUE_DIR}/sessions/")
        return
    
    print(f"📁 Found {len(session_files)} session file(s)")
    
    synced = 0
    skipped = 0
    
    for session_file in session_files:
        session = parse_continue_session(session_file)
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
        
        filename = f"continue-{date}-{time}-{session_id}.md"
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
