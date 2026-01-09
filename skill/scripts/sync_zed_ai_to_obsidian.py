#!/usr/bin/env python3
"""
Sync Zed AI sessions to Obsidian as markdown notes.
Zed stores conversations in:
- macOS: ~/.config/zed/conversations/
- Linux: ~/.config/zed/conversations/
"""

import json
import os
import re
from pathlib import Path
from datetime import datetime

# Paths
HOME = Path.home()
ZED_CONVERSATIONS = HOME / ".config/zed/conversations"
OBSIDIAN_VAULT = HOME / "Library/Mobile Documents/iCloud~md~obsidian/Documents/zettelkasten"
OUTPUT_DIR = OBSIDIAN_VAULT / "ai-sessions" / "zed-ai-sessions"

# Secret patterns to redact
SECRET_PATTERNS = [
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

def find_zed_conversations():
    """Find Zed AI conversation files."""
    if not ZED_CONVERSATIONS.exists():
        return []
    
    conversations = []
    for f in ZED_CONVERSATIONS.glob("*.json"):
        conversations.append(f)
    for f in ZED_CONVERSATIONS.glob("*.md"):
        conversations.append(f)
    
    return conversations

def parse_zed_conversation(file_path):
    """Parse a Zed AI conversation file."""
    if file_path.suffix == '.md':
        # Markdown format
        try:
            content = file_path.read_text(encoding='utf-8')
        except:
            return None
        
        # Parse markdown conversation
        messages = []
        current_role = None
        current_content = []
        
        for line in content.split('\n'):
            if line.startswith('## User') or line.startswith('## Human'):
                if current_role and current_content:
                    messages.append({
                        'role': current_role,
                        'content': '\n'.join(current_content).strip()
                    })
                current_role = 'user'
                current_content = []
            elif line.startswith('## Assistant') or line.startswith('## Zed'):
                if current_role and current_content:
                    messages.append({
                        'role': current_role,
                        'content': '\n'.join(current_content).strip()
                    })
                current_role = 'assistant'
                current_content = []
            elif current_role:
                current_content.append(line)
        
        if current_role and current_content:
            messages.append({
                'role': current_role,
                'content': '\n'.join(current_content).strip()
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
    else:
        # JSON format
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
        
        messages = []
        history = data.get('messages', data.get('history', []))
        
        for entry in history:
            if isinstance(entry, dict):
                role = entry.get('role', 'unknown')
                content = entry.get('content', entry.get('text', ''))
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
    """Convert a Zed AI session to markdown format."""
    messages = session.get('messages', [])
    if not messages:
        return None
    
    date = session.get('date', 'unknown')
    time = session.get('time', '00:00')
    session_id = session.get('session_id', 'unknown')
    
    first_user = next((m['content'][:80] for m in messages if m['role'] == 'user'), 'Session')
    first_user = first_user.replace('\n', ' ').replace('"', '\\"').strip()
    
    frontmatter = f'''---
type: zed-ai-session
date: {date}
time: "{time}"
session_id: "{session_id}"
tags:
  - zed
  - ai-session
  - coding
summary: "{first_user}..."
---
'''

    content = f'''# ⚡ Zed AI Session — {date} {time.replace(':', '')}

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
            content += f"## ⚡ Zed AI\n\n{text}\n\n---\n\n"
    
    content += "\n---\n*Session exported from Zed AI — secrets redacted*\n"
    
    return frontmatter + content

def main():
    """Main sync function."""
    print("🔄 Syncing Zed AI sessions to Obsidian...")
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    if not ZED_CONVERSATIONS.exists():
        print(f"📁 Zed conversations directory not found: {ZED_CONVERSATIONS}")
        return
    
    conversations = find_zed_conversations()
    
    if not conversations:
        print(f"📁 No Zed AI conversations found in {ZED_CONVERSATIONS}")
        return
    
    print(f"📁 Found {len(conversations)} conversation(s)")
    
    synced = 0
    skipped = 0
    
    for conv_file in conversations:
        session = parse_zed_conversation(conv_file)
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
        
        filename = f"zed-ai-{date}-{time}-{session_id}.md"
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
