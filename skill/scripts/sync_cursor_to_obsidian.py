#!/usr/bin/env python3
"""
Sync Cursor AI sessions to Obsidian Zettelkasten
Run: python3 ~/sync_cursor_to_obsidian.py
"""

import os
import re
import sys
from pathlib import Path
from datetime import datetime

# Add script directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from common import redact_secrets, get_obsidian_vault

# Configuration
CURSOR_PROJECTS = Path.home() / ".cursor" / "projects"
OBSIDIAN_VAULT = get_obsidian_vault()
OUTPUT_FOLDER = "ai-sessions/cursor-sessions"

def parse_transcript(file_path):
    """Parse a Cursor agent transcript file."""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    messages = []
    
    # Split by user/assistant turns
    # Format: "user:\n...\n\nA:\n..."
    parts = re.split(r'\n(?=user:|\nA:)', content)
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
        
        if part.startswith('user:'):
            # User message
            text = part[5:].strip()
            # Skip system messages
            if text.startswith('<external_links>'):
                # Extract just the user_query
                match = re.search(r'<user_query>\s*(.*?)\s*</user_query>', text, re.DOTALL)
                if match:
                    text = match.group(1).strip()
                else:
                    continue
            if text:
                messages.append({
                    'role': 'user',
                    'content': redact_secrets(text)
                })
        
        elif part.startswith('A:') or part.startswith('\nA:'):
            # Assistant message
            text = re.sub(r'^A:', '', part).strip()
            
            # Parse tool calls and thinking
            formatted_parts = []
            
            # Handle [Thinking] blocks
            thinking_matches = re.findall(r'\[Thinking\](.*?)(?=\[Tool call\]|\[Tool result\]|$)', text, re.DOTALL)
            for thinking in thinking_matches:
                if thinking.strip():
                    formatted_parts.append(f"> 💭 **Thinking:**\n> {thinking.strip()[:500]}...")
            
            # Handle [Tool call] blocks
            tool_matches = re.findall(r'\[Tool call\]\s*(\w+)\s*(.*?)(?=\[Tool call\]|\[Tool result\]|A:|\nuser:|$)', text, re.DOTALL)
            for tool_name, tool_args in tool_matches:
                args_clean = tool_args.strip()[:300]
                formatted_parts.append(f"**🔧 Tool:** `{tool_name}`\n```\n{redact_secrets(args_clean)}\n```")
            
            # Handle [Tool result] blocks
            result_matches = re.findall(r'\[Tool result\]\s*(\w+)\s*(.*?)(?=\[Tool call\]|\[Tool result\]|A:|\nuser:|$)', text, re.DOTALL)
            for result_name, result_content in result_matches:
                content_clean = result_content.strip()[:1000]
                formatted_parts.append(f"**📤 Result:** `{result_name}`\n```\n{redact_secrets(content_clean)}\n```")
            
            # Get remaining text (actual response)
            clean_text = re.sub(r'\[Thinking\].*?(?=\[Tool|\n\n|$)', '', text, flags=re.DOTALL)
            clean_text = re.sub(r'\[Tool call\].*?(?=\[Tool|\n\n|$)', '', clean_text, flags=re.DOTALL)
            clean_text = re.sub(r'\[Tool result\].*?(?=\[Tool|\n\n|$)', '', clean_text, flags=re.DOTALL)
            clean_text = clean_text.strip()
            
            if clean_text:
                formatted_parts.append(redact_secrets(clean_text))
            
            if formatted_parts:
                messages.append({
                    'role': 'assistant',
                    'content': '\n\n'.join(formatted_parts)
                })
    
    return messages

def get_project_name(file_path):
    """Extract project name from file path."""
    # Path like: .cursor/projects/Users-username-Documents-GitHub-project/agent-transcripts/...
    parts = str(file_path).split('/')
    for i, part in enumerate(parts):
        if part == 'projects' and i + 1 < len(parts):
            project = parts[i + 1]
            # Clean up the project name - remove Users-<username>- prefix dynamically
            username = os.environ.get('USER', '')
            if username:
                project = project.replace(f'Users-{username}-', '')
            # Convert hyphens to slashes for path-like display
            project = project.replace('-', '/')
            return project
    return "Unknown"

def generate_markdown(messages, file_path):
    """Generate markdown for a session."""
    session_id = file_path.stem[:8]
    project = get_project_name(file_path)
    
    # Get file modification time as session date
    mtime = os.path.getmtime(file_path)
    dt = datetime.fromtimestamp(mtime)
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
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Find all transcript files
    transcript_files = list(CURSOR_PROJECTS.rglob("agent-transcripts/*.txt"))
    print(f"📁 Found {len(transcript_files)} session files")
    
    synced = 0
    skipped = 0
    
    for file_path in sorted(transcript_files):
        messages = parse_transcript(file_path)
        
        if not messages:
            skipped += 1
            continue
        
        # Filter out empty sessions
        user_messages = [m for m in messages if m['role'] == 'user' and m['content']]
        if len(user_messages) < 1:
            skipped += 1
            continue
        
        md_content, title_date, session_id = generate_markdown(messages, file_path)
        
        # Create kebab-case filename
        project_short = get_project_name(file_path).replace('/', '-')[:30].lower()
        date_kebab = title_date.replace(' ', '-')
        filename = f"cursor-{date_kebab}-{project_short}-{session_id}".lower()
        
        # Check if already synced (skip existing files)
        note_path = output_path / f"{filename}.md"
        if note_path.exists():
            skipped += 1
            continue
        
        # Write markdown
        note_path.write_text(md_content, encoding='utf-8')
        synced += 1
        print(f"  ✅ {filename}")
    
    print(f"\n✅ Synced {synced} new sessions ({skipped} skipped)")
    print(f"📂 Output: {output_path}")

if __name__ == "__main__":
    main()
