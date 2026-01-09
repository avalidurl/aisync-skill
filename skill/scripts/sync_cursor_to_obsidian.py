#!/usr/bin/env python3
"""
Sync Cursor AI sessions to Obsidian Zettelkasten
Run: python3 ~/sync_cursor_to_obsidian.py
"""

import json
import os
import re
from pathlib import Path
from datetime import datetime

# Configuration
CURSOR_PROJECTS = Path.home() / ".cursor" / "projects"
OBSIDIAN_VAULT = Path.home() / "Library/Mobile Documents/iCloud~md~obsidian/Documents/zettelkasten"
OUTPUT_FOLDER = "ai-sessions/cursor-sessions"

# Secret patterns (same as Codex)
SECRET_PATTERNS = [
    (r'sk-[a-zA-Z0-9]{20,}', '[REDACTED: OpenAI API Key]'),
    (r'sk-proj-[a-zA-Z0-9\-_]{50,}', '[REDACTED: OpenAI Project Key]'),
    (r'sk-ant-[a-zA-Z0-9\-_]{50,}', '[REDACTED: Anthropic API Key]'),
    (r'xai-[a-zA-Z0-9]{20,}', '[REDACTED: xAI API Key]'),
    (r'AIza[a-zA-Z0-9\-_]{35}', '[REDACTED: Google API Key]'),
    (r'AKIA[A-Z0-9]{16}', '[REDACTED: AWS Access Key]'),
    (r'ghp_[a-zA-Z0-9]{36}', '[REDACTED: GitHub Token]'),
    (r'gho_[a-zA-Z0-9]{36}', '[REDACTED: GitHub OAuth Token]'),
    (r'github_pat_[a-zA-Z0-9_]{22,}', '[REDACTED: GitHub PAT]'),
    (r'glpat-[a-zA-Z0-9\-_]{20,}', '[REDACTED: GitLab Token]'),
    (r'npm_[a-zA-Z0-9]{36}', '[REDACTED: NPM Token]'),
    (r'xox[baprs]-[a-zA-Z0-9\-]{10,}', '[REDACTED: Slack Token]'),
    (r'sk_live_[a-zA-Z0-9]{24,}', '[REDACTED: Stripe Live Key]'),
    (r'sk_test_[a-zA-Z0-9]{24,}', '[REDACTED: Stripe Test Key]'),
    (r'Bearer [a-zA-Z0-9\-_\.]{20,}', '[REDACTED: Bearer Token]'),
    (r'-----BEGIN (RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY( BLOCK)?-----[\s\S]*?-----END (RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY( BLOCK)?-----', '[REDACTED: Private Key Block]'),
    (r'-----BEGIN CERTIFICATE-----[\s\S]*?-----END CERTIFICATE-----', '[REDACTED: Certificate Block]'),
    (r'(password|passwd|pwd|secret|token|api_key|apikey|api-key|auth_token|access_token|refresh_token)\s*[=:]\s*["\']?[a-zA-Z0-9\-_\.!@#$%^&*]{8,}["\']?', '[REDACTED: Credential]'),
    (r'(mysql|postgres|postgresql|mongodb|redis|amqp)://[^:]+:[^@]+@[^\s]+', '[REDACTED: Database URL]'),
    (r'eyJ[a-zA-Z0-9\-_]+\.eyJ[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+', '[REDACTED: JWT Token]'),
]

def redact_secrets(text):
    """Redact sensitive information from text."""
    if not text:
        return text
    for pattern, replacement in SECRET_PATTERNS:
        try:
            text = re.sub(pattern, replacement, text, flags=re.MULTILINE | re.IGNORECASE)
        except:
            pass
    return text

def parse_transcript(file_path):
    """Parse a Cursor agent transcript file into exchanges (user + assistant pairs)."""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    messages = []
    
    # Split by user turns - each user: starts a new exchange
    user_splits = re.split(r'\n(?=user:)', content)
    
    for section in user_splits:
        section = section.strip()
        if not section or not section.startswith('user:'):
            continue
        
        # Split this section into user part and assistant parts
        parts = re.split(r'\n\n(?=assistant:)', section, maxsplit=1)
        
        # Parse user message
        user_part = parts[0]
        user_text = user_part[5:].strip()  # Remove 'user:'
        
        # Extract user_query if present
        if '<user_query>' in user_text:
            match = re.search(r'<user_query>\s*(.*?)\s*</user_query>', user_text, re.DOTALL)
            if match:
                user_text = match.group(1).strip()
            else:
                continue
        
        if not user_text or len(user_text) < 3:
            continue
            
        messages.append({
            'role': 'user',
            'content': redact_secrets(user_text)
        })
        
        # Parse all assistant blocks as ONE response
        if len(parts) > 1:
            assistant_section = parts[1]
            # Get all assistant blocks
            assistant_blocks = re.findall(r'assistant:\s*(.*?)(?=\nassistant:|\Z)', assistant_section, re.DOTALL)
            
            all_assistant_content = []
            for block in assistant_blocks:
                block = block.strip()
                if not block:
                    continue
                    
                # Parse and format the block
                formatted = format_assistant_block(block)
                if formatted:
                    all_assistant_content.append(formatted)
            
            if all_assistant_content:
                # Combine all assistant blocks into one response
                messages.append({
                    'role': 'assistant', 
                    'content': '\n\n---\n\n'.join(all_assistant_content)
                })
    
    return messages

def format_assistant_block(text):
    """Format an assistant block with tool calls and thinking."""
    formatted_parts = []
    
    # Handle [Thinking] blocks - just get the last thinking
    thinking_matches = re.findall(r'\[Thinking\](.*?)(?=\[Tool call\]|\[Tool result\]|$)', text, re.DOTALL)
    if thinking_matches:
        last_thinking = thinking_matches[-1].strip()[:500]
        if last_thinking:
            formatted_parts.append(f"> 💭 **Thinking:** {last_thinking}...")
    
    # Handle [Tool call] blocks
    tool_matches = re.findall(r'\[Tool call\]\s*(\w+)\s*(.*?)(?=\[Tool call\]|\[Tool result\]|\nuser:|$)', text, re.DOTALL)
    for tool_name, tool_args in tool_matches:
        args_clean = tool_args.strip()[:200]
        formatted_parts.append(f"**🔧 Tool:** `{tool_name}`")
    
    # Get clean response text (remove thinking and tool blocks)
    clean_text = re.sub(r'\[Thinking\].*?(?=\[Tool|\n\n|$)', '', text, flags=re.DOTALL)
    clean_text = re.sub(r'\[Tool call\].*?(?=\[Tool|\n\n|$)', '', clean_text, flags=re.DOTALL)
    clean_text = re.sub(r'\[Tool result\].*?(?=\[Tool|\n\n|$)', '', clean_text, flags=re.DOTALL)
    clean_text = clean_text.strip()
    
    if clean_text and len(clean_text) > 10:
        formatted_parts.append(redact_secrets(clean_text))
    
    return '\n\n'.join(formatted_parts) if formatted_parts else None

def get_project_name(file_path):
    """Extract project name from file path."""
    # Path like: .cursor/projects/Users-gokhanturhan-Documents-GitHub-gokhan-memex/agent-transcripts/...
    parts = str(file_path).split('/')
    for i, part in enumerate(parts):
        if part == 'projects' and i + 1 < len(parts):
            project = parts[i + 1]
            # Clean up the project name
            project = project.replace('Users-gokhanturhan-', '')
            project = project.replace('-', '/')
            return project
    return "Unknown"

def get_file_created_at(file_path):
    """Get file creation time (birthtime on macOS, fallback to mtime)."""
    stat = file_path.stat()
    # Try birthtime first (macOS)
    if hasattr(stat, 'st_birthtime') and stat.st_birthtime > 0:
        return datetime.fromtimestamp(stat.st_birthtime)
    # Fallback to mtime
    return datetime.fromtimestamp(stat.st_mtime)

def generate_markdown(messages, file_path):
    """Generate markdown for a session."""
    session_id = file_path.stem[:8]
    project = get_project_name(file_path)
    
    # Use birthtime for stable filename, not mtime
    dt = get_file_created_at(file_path)
    date_str = dt.strftime('%Y-%m-%d')
    time_str = dt.strftime('%H:%M')
    title_date = dt.strftime('%Y-%m-%d %H%M')
    
    # Get first user message as summary
    first_msg = ""
    for m in messages:
        if m['role'] == 'user' and m['content'] and len(m['content']) > 5:
            first_msg = m['content'][:100].replace('\n', ' ').strip()
            break
    
    md = f'''---
type: cursor-session
date: {date_str}
time: "{time_str}"
session_id: "{session_id}"
project: "{project}"
tags:
  - cursor
  - ai-session
  - coding
summary: "{first_msg[:80]}..."
---

# 🖱️ Cursor Session — {title_date}

| Property | Value |
|----------|-------|
| **Date** | {date_str} {time_str} |
| **Session ID** | `{session_id}` |
| **Project** | `{project}` |

---

'''
    
    for msg in messages:
        role = msg['role']
        content = msg['content']
        
        if not content or not content.strip():
            continue
        
        if role == 'user':
            md += f"## 👤 User\n\n{content}\n\n---\n\n"
        elif role == 'assistant':
            md += f"## 🤖 Cursor\n\n{content}\n\n---\n\n"
    
    md += f"\n---\n*Session exported from Cursor — secrets redacted*\n"
    
    return md, title_date, session_id

def main():
    print("🔄 Syncing Cursor sessions to Obsidian...")
    print("🔒 Redacting secrets, tokens, and API keys...")
    
    # Create output folder
    output_path = OBSIDIAN_VAULT / OUTPUT_FOLDER
    output_path.mkdir(exist_ok=True)
    
    # Find all transcript files
    transcript_files = list(CURSOR_PROJECTS.rglob("agent-transcripts/*.txt"))
    print(f"📁 Found {len(transcript_files)} session files")
    
    new_count = 0
    
    for file_path in sorted(transcript_files):
        messages = parse_transcript(file_path)
        
        if not messages:
            continue
        
        # Filter out empty sessions
        user_messages = [m for m in messages if m['role'] == 'user' and m['content']]
        if len(user_messages) < 1:
            continue
        
        md_content, title_date, session_id = generate_markdown(messages, file_path)
        
        # Create kebab-case filename
        project_short = get_project_name(file_path).replace('/', '-')[:30].lower()
        date_kebab = title_date.replace(' ', '-')
        filename = f"cursor-{date_kebab}-{project_short}-{session_id}".lower()
        
        # Find existing files with same session ID (handles filename changes)
        existing_files = list(output_path.glob(f"*{session_id}*.md"))
        source_mtime = file_path.stat().st_mtime
        
        note_path = output_path / f"{filename}.md"
        
        if existing_files:
            # Use the existing file (prefer exact match, else first found)
            existing_file = next((f for f in existing_files if f.name == f"{filename}.md"), existing_files[0])
            
            # Check if source has been modified since last sync
            if source_mtime <= existing_file.stat().st_mtime:
                continue  # Skip - no changes
            
            # APPEND mode: Read existing note, count exchanges, append only new ones
            existing_content = existing_file.read_text(encoding='utf-8')
            
            # Count by USER exchanges (headers at line start only)
            existing_user_count = len(re.findall(r'^## 👤 User$', existing_content, re.MULTILINE))
            source_user_count = sum(1 for m in messages if m['role'] == 'user')
            
            if source_user_count > existing_user_count:
                # Find new exchanges: messages after the last synced user exchange
                # Build list of exchange indices
                new_messages = []
                user_idx = 0
                for msg in messages:
                    if msg['role'] == 'user':
                        user_idx += 1
                    if user_idx > existing_user_count:
                        new_messages.append(msg)
                
                # Find the sync footer and insert before it, or append at end
                footer_marker = "\n---\n*Session exported from Cursor"
                
                append_content = ""
                for msg in new_messages:
                    role = msg['role']
                    content = msg['content']
                    if not content or not content.strip():
                        continue
                    if role == 'user':
                        append_content += f"## 👤 User\n\n{content}\n\n---\n\n"
                    elif role == 'assistant':
                        append_content += f"## 🤖 Cursor\n\n{content}\n\n---\n\n"
                
                if append_content:
                    if footer_marker in existing_content:
                        # Insert before footer
                        updated_content = existing_content.replace(footer_marker, append_content + footer_marker)
                    else:
                        # Append at end
                        updated_content = existing_content + "\n" + append_content
                    
                    existing_file.write_text(updated_content, encoding='utf-8')
                    new_count += 1
                    print(f"  ✅ {existing_file.name} (+{len(new_messages)} messages)")
            continue
        
        # New session - create file
        note_path.write_text(md_content, encoding='utf-8')
        new_count += 1
        print(f"  ✅ {filename} (new)")
    
    print(f"\n✅ Synced {new_count} sessions to {OUTPUT_FOLDER}/")

def create_index(output_path):
    """Create an index of all sessions."""
    sessions = sorted(output_path.glob("Cursor *.md"), reverse=True)
    
    index_md = f'''---
aliases: [cursor, cursor sessions]
tags: [index, MOC, cursor]
---

# 🖱️ Cursor Sessions

> **Total sessions:** {len(sessions)} | **Last synced:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Recent Sessions

| Date | Project | Session |
|------|---------|---------|
'''
    
    for session in sessions[:100]:
        name = session.stem
        # Parse filename "Cursor 2026-01-08 1921 project-name abc123"
        parts = name.split(' ')
        date = parts[1] if len(parts) > 1 else ""
        time = parts[2] if len(parts) > 2 else ""
        project = parts[3] if len(parts) > 3 else ""
        
        time_fmt = f"{time[:2]}:{time[2:]}" if len(time) == 4 else time
        
        index_md += f"| {date} {time_fmt} | {project} | [[{OUTPUT_FOLDER}/{name}\\|📝 View]] |\n"
    
    index_md += f'''

---

## Sync Command

```bash
python3 ~/sync_cursor_to_obsidian.py
```

*All secrets, API keys, and tokens are automatically redacted*
'''
    
    index_path = output_path.parent / "Cursor Sessions.md"
    index_path.write_text(index_md, encoding='utf-8')

if __name__ == "__main__":
    main()
