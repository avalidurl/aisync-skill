#!/usr/bin/env python3
"""
Sync Cline (Claude Dev) sessions to Obsidian as markdown notes.
Cline stores tasks in VS Code's globalStorage:
- macOS: ~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/tasks/
- Linux: ~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/tasks/
- Windows: %APPDATA%/Code/User/globalStorage/saoudrizwan.claude-dev/tasks/
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
OUTPUT_DIR = OBSIDIAN_VAULT / "ai-sessions" / "cline-sessions"

# Platform-specific Cline storage paths
def get_cline_paths():
    """Get Cline storage paths for the current platform."""
    system = platform.system()
    paths = []
    
    if system == "Darwin":  # macOS
        paths.append(HOME / "Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/tasks")
        paths.append(HOME / "Library/Application Support/Cursor/User/globalStorage/saoudrizwan.claude-dev/tasks")
    elif system == "Linux":
        paths.append(HOME / ".config/Code/User/globalStorage/saoudrizwan.claude-dev/tasks")
        paths.append(HOME / ".config/Cursor/User/globalStorage/saoudrizwan.claude-dev/tasks")
    elif system == "Windows":
        appdata = Path(os.environ.get('APPDATA', ''))
        paths.append(appdata / "Code/User/globalStorage/saoudrizwan.claude-dev/tasks")
        paths.append(appdata / "Cursor/User/globalStorage/saoudrizwan.claude-dev/tasks")
    
    return [p for p in paths if p.exists()]

# Secret patterns to redact
SECRET_PATTERNS = [
    (r'sk-[a-zA-Z0-9]{20,}', '[REDACTED: OpenAI API Key]'),
    (r'sk-ant-[a-zA-Z0-9-]{20,}', '[REDACTED: Anthropic API Key]'),
    (r'ghp_[a-zA-Z0-9]{36,}', '[REDACTED: GitHub PAT]'),
    (r'Bearer\s+[a-zA-Z0-9._-]{20,}', '[REDACTED: Bearer Token]'),
    (r'eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*', '[REDACTED: JWT Token]'),
    (r'postgres://[^\s]+', '[REDACTED: Database URL]'),
    (r'mongodb(\+srv)?://[^\s]+', '[REDACTED: MongoDB URL]'),
]

def redact_secrets(text):
    """Redact sensitive information from text."""
    if not text:
        return text
    for pattern, replacement in SECRET_PATTERNS:
        text = re.sub(pattern, replacement, text)
    return text

def extract_text_content(content):
    """Extract text from Cline's content array (similar to Claude API format)."""
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
                    # Skip environment_details blocks
                    if '<environment_details>' in text:
                        # Extract just user message if present
                        match = re.search(r'<task>\s*(.*?)\s*</task>', text, re.DOTALL)
                        if match:
                            parts.append(match.group(1).strip())
                    else:
                        parts.append(text)
                elif item.get('type') == 'tool_use':
                    tool_name = item.get('name', 'tool')
                    parts.append(f"**🔧 Tool: {tool_name}**")
                    if item.get('input'):
                        input_str = json.dumps(item['input'], indent=2)[:500] if isinstance(item['input'], dict) else str(item['input'])[:500]
                        parts.append(f"```\n{input_str}\n```")
                elif item.get('type') == 'tool_result':
                    result = item.get('content', '')
                    if result:
                        result_str = str(result)[:1000]
                        parts.append(f"**📤 Result:**\n```\n{result_str}\n```")
        return '\n\n'.join(parts)
    
    return str(content) if content else ''

def parse_cline_task(task_dir):
    """Parse a Cline task directory."""
    conversation_file = task_dir / "api_conversation_history.json"
    metadata_file = task_dir / "task_metadata.json"
    
    if not conversation_file.exists():
        return None
    
    try:
        with open(conversation_file, 'r', encoding='utf-8') as f:
            conversation = json.load(f)
    except (json.JSONDecodeError, IOError):
        return None
    
    # Load metadata if available
    metadata = {}
    if metadata_file.exists():
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        except:
            pass
    
    # Extract model info
    model = "unknown"
    model_usage = metadata.get('model_usage', [])
    if model_usage and len(model_usage) > 0:
        model = model_usage[0].get('model_id', 'unknown')
    
    # Parse messages
    messages = []
    for entry in conversation:
        role = entry.get('role', '')
        content = entry.get('content', [])
        
        text = extract_text_content(content)
        if text and text.strip():
            # Clean up the text
            text = text.strip()
            if len(text) > 10:  # Skip very short messages
                messages.append({
                    'role': 'user' if role == 'user' else 'assistant',
                    'content': text
                })
    
    if not messages:
        return None
    
    # Get task creation time from directory name (timestamp)
    task_id = task_dir.name
    try:
        # Task ID is a timestamp in milliseconds
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
        'model': model,
        'messages': messages,
        'source_dir': str(task_dir)
    }

def task_to_markdown(task):
    """Convert a Cline task to markdown format."""
    messages = task.get('messages', [])
    if not messages:
        return None
    
    date = task.get('date', 'unknown')
    time = task.get('time', '00:00')
    task_id = task.get('task_id', 'unknown')
    model = task.get('model', 'unknown')
    
    # Get first user message as summary
    first_user = next((m['content'][:80] for m in messages if m['role'] == 'user'), 'Task')
    first_user = first_user.replace('\n', ' ').replace('"', '\\"').strip()
    
    frontmatter = f'''---
type: cline-session
date: {date}
time: "{time}"
task_id: "{task_id}"
model: "{model}"
tags:
  - cline
  - claude-dev
  - ai-session
  - coding
summary: "{first_user}..."
---
'''

    content = f'''# 🤖 Cline Session — {date} {time.replace(':', '')}

| Property | Value |
|----------|-------|
| **Date** | {date} {time} |
| **Task ID** | `{task_id}` |
| **Model** | {model} |

---

'''

    for msg in messages:
        text = redact_secrets(msg['content'])
        if msg['role'] == 'user':
            content += f"## 👤 User\n\n{text}\n\n---\n\n"
        else:
            content += f"## 🤖 Cline\n\n{text}\n\n---\n\n"
    
    content += "\n---\n*Session exported from Cline (Claude Dev) — secrets redacted*\n"
    
    return frontmatter + content

def main():
    """Main sync function."""
    print("🔄 Syncing Cline sessions to Obsidian...")
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Find Cline storage paths
    cline_paths = get_cline_paths()
    
    if not cline_paths:
        print("📁 No Cline tasks directory found")
        print("   Cline stores tasks in VS Code's globalStorage/saoudrizwan.claude-dev/tasks/")
        return
    
    print(f"📁 Found {len(cline_paths)} Cline storage location(s)")
    
    synced = 0
    skipped = 0
    
    for tasks_dir in cline_paths:
        print(f"   Scanning: {tasks_dir}")
        
        for task_dir in tasks_dir.iterdir():
            if not task_dir.is_dir():
                continue
            
            task = parse_cline_task(task_dir)
            if not task:
                skipped += 1
                continue
            
            markdown = task_to_markdown(task)
            if not markdown:
                skipped += 1
                continue
            
            # Generate filename
            date = task.get('date', 'unknown')
            time = task.get('time', '0000').replace(':', '')
            task_id = task.get('task_id', 'unknown')
            
            filename = f"cline-{date}-{time}-{task_id}.md"
            output_path = OUTPUT_DIR / filename
            
            # Check if already synced AND source hasn't been modified
            if output_path.exists():
                source_mtime = Path(task['source_dir']).stat().st_mtime
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
