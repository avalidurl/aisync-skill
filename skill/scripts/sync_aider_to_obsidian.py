#!/usr/bin/env python3
"""
Sync Aider sessions to Obsidian as markdown notes.
Aider stores chat history in:
- Global: ~/.aider.chat.history.md
- Per-project: .aider.chat.history.md in project roots
"""

import os
import re
from pathlib import Path
from datetime import datetime
import hashlib

# Paths
HOME = Path.home()
OBSIDIAN_VAULT = HOME / "Library/Mobile Documents/iCloud~md~obsidian/Documents/zettelkasten"
OUTPUT_DIR = OBSIDIAN_VAULT / "ai-sessions" / "aider-sessions"

# Global history file
GLOBAL_HISTORY = HOME / ".aider.chat.history.md"

# Matchers for credential-shaped text. The label is documentation only
# and is never written into a note or a log line.
REDACTION_PATTERNS = [
    (r'sk-[a-zA-Z0-9]{20,}', '[REDACTED: OpenAI API Key]'),
    (r'sk-ant-[a-zA-Z0-9-]{20,}', '[REDACTED: Anthropic API Key]'),
    (r'ghp_[a-zA-Z0-9]{36,}', '[REDACTED: GitHub PAT]'),
    (r'Bearer\s+[a-zA-Z0-9._-]{20,}', '[REDACTED: Bearer Token]'),
    (r'eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*', '[REDACTED: JWT Token]'),
    (r'postgres://[^\s]+', '[REDACTED: Database URL]'),
    (r'mongodb(\+srv)?://[^\s]+', '[REDACTED: MongoDB URL]'),
]

def redact_secrets(text):
    """Replace credential-shaped substrings before text is stored or logged.

    The stored value is the literal "[redacted]". It is not taken from
    REDACTION_PATTERNS, so the matcher list itself is not written out.
    """
    if not text:
        return text
    for pattern, _kind in REDACTION_PATTERNS:
        text = re.sub(pattern, "[redacted]", text)
    return text

def parse_aider_history(file_path):
    """
    Parse Aider's markdown chat history.
    Aider format:
    #### user message
    content...
    
    #### assistant message  
    content...
    """
    if not file_path.exists():
        return []
    
    content = file_path.read_text(encoding='utf-8', errors='ignore')
    
    # Split by message markers
    # Aider uses "#### " prefix for messages
    sessions = []
    current_session = []
    current_date = None
    
    lines = content.split('\n')
    current_role = None
    current_content = []
    
    for line in lines:
        # Check for date markers (Aider sometimes includes timestamps)
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', line)
        if date_match and not current_date:
            current_date = date_match.group(1)
        
        # Check for role markers
        if line.startswith('#### '):
            # Save previous message
            if current_role and current_content:
                current_session.append({
                    'role': current_role,
                    'content': '\n'.join(current_content).strip()
                })
            
            # Determine new role
            role_text = line[5:].lower().strip()
            if 'user' in role_text or 'human' in role_text:
                current_role = 'user'
            elif 'assistant' in role_text or 'aider' in role_text or 'claude' in role_text or 'gpt' in role_text:
                current_role = 'assistant'
            else:
                current_role = 'user'  # Default
            current_content = []
        elif line.startswith('---') and len(line) > 5:
            # Session separator - save current session
            if current_role and current_content:
                current_session.append({
                    'role': current_role,
                    'content': '\n'.join(current_content).strip()
                })
            if current_session:
                sessions.append({
                    'date': current_date or 'unknown',
                    'messages': current_session
                })
            current_session = []
            current_role = None
            current_content = []
            current_date = None
        else:
            if current_role:
                current_content.append(line)
    
    # Don't forget the last message/session
    if current_role and current_content:
        current_session.append({
            'role': current_role,
            'content': '\n'.join(current_content).strip()
        })
    if current_session:
        sessions.append({
            'date': current_date or datetime.now().strftime('%Y-%m-%d'),
            'messages': current_session
        })
    
    return sessions

def find_project_histories():
    """Find all .aider.chat.history.md files in common project directories."""
    project_dirs = [
        HOME / "Documents",
        HOME / "Projects", 
        HOME / "Code",
        HOME / "Developer",
        HOME / "GitHub",
        HOME / "Documents" / "GitHub",
    ]
    
    history_files = []
    
    for base_dir in project_dirs:
        if base_dir.exists():
            for history_file in base_dir.rglob(".aider.chat.history.md"):
                history_files.append(history_file)
    
    return history_files

def session_to_markdown(session, source_file, session_idx):
    """Convert an Aider session to markdown format."""
    messages = session.get('messages', [])
    if not messages:
        return None
    
    date = session.get('date', 'unknown')
    
    # Generate unique ID from content
    content_hash = hashlib.md5(str(messages).encode()).hexdigest()[:8]
    
    # Get project name from source file path
    if source_file == GLOBAL_HISTORY:
        project = "global"
    else:
        project = source_file.parent.name
    
    # Get first user message as summary. Redact before truncating so a
    # credential that spans the cut is not left in the frontmatter.
    first_user = next((m['content'] for m in messages if m['role'] == 'user'), 'Session')
    first_user = redact_secrets(first_user).replace('\n', ' ').strip()[:80]
    
    frontmatter = f'''---
type: aider-session
date: {date}
session_idx: {session_idx}
project: "{project}"
source_file: "{source_file}"
tags:
  - aider
  - ai-session
  - coding
summary: "{first_user}..."
---
'''

    content = f'''# 🔧 Aider Session — {date}

| Property | Value |
|----------|-------|
| **Date** | {date} |
| **Project** | `{project}` |
| **Session** | #{session_idx} |

---

'''

    for msg in messages:
        text = redact_secrets(msg['content'])
        if msg['role'] == 'user':
            content += f"## 👤 User\n\n{text}\n\n---\n\n"
        else:
            content += f"## 🤖 Aider\n\n{text}\n\n---\n\n"
    
    content += "\n---\n*Session exported from Aider — secrets redacted*\n"
    
    return frontmatter + content, content_hash

def main():
    """Main sync function."""
    print("🔄 Syncing Aider sessions to Obsidian...")
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Collect all history files
    history_files = []
    
    if GLOBAL_HISTORY.exists():
        history_files.append(GLOBAL_HISTORY)
    
    history_files.extend(find_project_histories())
    
    if not history_files:
        print("📁 No Aider history files found")
        print(f"   Looked for: {GLOBAL_HISTORY}")
        print("   And .aider.chat.history.md in project directories")
        return
    
    print(f"📁 Found {len(history_files)} history file(s)")
    
    synced = 0
    skipped = 0
    
    for history_file in history_files:
        sessions = parse_aider_history(history_file)
        
        for idx, session in enumerate(sessions, 1):
            result = session_to_markdown(session, history_file, idx)
            if not result:
                skipped += 1
                continue
            
            markdown, content_hash = result
            date = session.get('date', 'unknown')
            
            # Generate filename
            if history_file == GLOBAL_HISTORY:
                project_slug = "global"
            else:
                project_slug = history_file.parent.name.lower()[:20]
            
            filename = f"aider-{date}-{project_slug}-{idx:03d}-{content_hash}.md"
            output_path = OUTPUT_DIR / filename
            
            # Check if already synced
            if output_path.exists():
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
