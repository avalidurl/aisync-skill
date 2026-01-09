#!/usr/bin/env python3
"""
Sync Roo Code (Roo Cline) sessions to Obsidian as markdown notes.
Roo Code stores tasks in VS Code's globalStorage:
- macOS: ~/Library/Application Support/Code/User/globalStorage/rooveterinaryinc.roo-cline/tasks/
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
OUTPUT_DIR = OBSIDIAN_VAULT / "ai-sessions" / "roo-code-sessions"

def get_roo_paths():
    """Get Roo Code storage paths for the current platform."""
    system = platform.system()
    paths = []
    
    if system == "Darwin":  # macOS
        paths.append(HOME / "Library/Application Support/Code/User/globalStorage/rooveterinaryinc.roo-cline/tasks")
        paths.append(HOME / "Library/Application Support/Cursor/User/globalStorage/rooveterinaryinc.roo-cline/tasks")
    elif system == "Linux":
        paths.append(HOME / ".config/Code/User/globalStorage/rooveterinaryinc.roo-cline/tasks")
    elif system == "Windows":
        appdata = Path(os.environ.get('APPDATA', ''))
        paths.append(appdata / "Code/User/globalStorage/rooveterinaryinc.roo-cline/tasks")
    
    return [p for p in paths if p.exists()]

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

def extract_text_content(content):
    """Extract text from content array."""
    if isinstance(content, str):
        return content
    
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                if item.get('type') == 'text':
                    text = item.get('text', '')
                    if '<environment_details>' not in text:
                        parts.append(text)
                    else:
                        match = re.search(r'<task>\s*(.*?)\s*</task>', text, re.DOTALL)
                        if match:
                            parts.append(match.group(1).strip())
        return '\n\n'.join(parts)
    
    return str(content) if content else ''

def parse_roo_task(task_dir):
    """Parse a Roo Code task directory."""
    conversation_file = task_dir / "api_conversation_history.json"
    
    if not conversation_file.exists():
        return None
    
    try:
        with open(conversation_file, 'r', encoding='utf-8') as f:
            conversation = json.load(f)
    except (json.JSONDecodeError, IOError):
        return None
    
    messages = []
    for entry in conversation:
        role = entry.get('role', '')
        content = entry.get('content', [])
        
        text = extract_text_content(content)
        if text and text.strip() and len(text) > 10:
            messages.append({
                'role': 'user' if role == 'user' else 'assistant',
                'content': text.strip()
            })
    
    if not messages:
        return None
    
    task_id = task_dir.name
    try:
        timestamp = int(task_id) / 1000
        dt = datetime.fromtimestamp(timestamp)
        date = dt.strftime('%Y-%m-%d')
        time = dt.strftime('%H:%M')
    except:
        date = 'unknown'
        time = '00:00'
    
    return {
        'task_id': task_id[:8],
        'date': date,
        'time': time,
        'messages': messages,
        'source_dir': str(task_dir)
    }

def task_to_markdown(task):
    """Convert a Roo Code task to markdown format."""
    messages = task.get('messages', [])
    if not messages:
        return None
    
    date = task.get('date', 'unknown')
    time = task.get('time', '00:00')
    task_id = task.get('task_id', 'unknown')
    
    first_user = next((m['content'][:80] for m in messages if m['role'] == 'user'), 'Task')
    first_user = first_user.replace('\n', ' ').replace('"', '\\"').strip()
    
    frontmatter = f'''---
type: roo-code-session
date: {date}
time: "{time}"
task_id: "{task_id}"
tags:
  - roo-code
  - ai-session
  - coding
summary: "{first_user}..."
---
'''

    content = f'''# 🦘 Roo Code Session — {date} {time.replace(':', '')}

| Property | Value |
|----------|-------|
| **Date** | {date} {time} |
| **Task ID** | `{task_id}` |

---

'''

    for msg in messages:
        text = redact_secrets(msg['content'])
        if msg['role'] == 'user':
            content += f"## 👤 User\n\n{text}\n\n---\n\n"
        else:
            content += f"## 🦘 Roo Code\n\n{text}\n\n---\n\n"
    
    content += "\n---\n*Session exported from Roo Code — secrets redacted*\n"
    
    return frontmatter + content

def main():
    """Main sync function."""
    print("🔄 Syncing Roo Code sessions to Obsidian...")
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    roo_paths = get_roo_paths()
    
    if not roo_paths:
        print("📁 No Roo Code tasks directory found")
        return
    
    print(f"📁 Found {len(roo_paths)} Roo Code storage location(s)")
    
    synced = 0
    skipped = 0
    
    for tasks_dir in roo_paths:
        print(f"   Scanning: {tasks_dir}")
        
        for task_dir in tasks_dir.iterdir():
            if not task_dir.is_dir():
                continue
            
            task = parse_roo_task(task_dir)
            if not task:
                skipped += 1
                continue
            
            markdown = task_to_markdown(task)
            if not markdown:
                skipped += 1
                continue
            
            date = task.get('date', 'unknown')
            time = task.get('time', '0000').replace(':', '')
            task_id = task.get('task_id', 'unknown')
            
            filename = f"roo-code-{date}-{time}-{task_id}.md"
            output_path = OUTPUT_DIR / filename
            
            if output_path.exists():
                source_mtime = Path(task['source_dir']).stat().st_mtime
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
