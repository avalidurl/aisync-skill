#!/usr/bin/env python3
"""
Sync Claude Code sessions to Obsidian as markdown notes.
Includes secret redaction for security.
"""

import json
import os
import re
from pathlib import Path
from datetime import datetime

# Paths
CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"
OBSIDIAN_VAULT = Path.home() / "Library/Mobile Documents/iCloud~md~obsidian/Documents/zettelkasten"
OUTPUT_DIR = OBSIDIAN_VAULT / "ai-sessions" / "claude-code-sessions"

# Secret patterns to redact
SECRET_PATTERNS = [
    (r'sk-[a-zA-Z0-9]{20,}', '[REDACTED: OpenAI API Key]'),
    (r'sk-ant-[a-zA-Z0-9-]{20,}', '[REDACTED: Anthropic API Key]'),
    (r'ghp_[a-zA-Z0-9]{36,}', '[REDACTED: GitHub PAT]'),
    (r'github_pat_[a-zA-Z0-9_]{20,}', '[REDACTED: GitHub PAT]'),
    (r'gho_[a-zA-Z0-9]{36,}', '[REDACTED: GitHub OAuth]'),
    (r'xoxb-[a-zA-Z0-9-]+', '[REDACTED: Slack Bot Token]'),
    (r'xoxp-[a-zA-Z0-9-]+', '[REDACTED: Slack User Token]'),
    (r'Bearer\s+[a-zA-Z0-9._-]{20,}', '[REDACTED: Bearer Token]'),
    (r'eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*', '[REDACTED: JWT Token]'),
    (r'AKIA[0-9A-Z]{16}', '[REDACTED: AWS Access Key]'),
    (r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----[\s\S]*?-----END\s+(RSA\s+)?PRIVATE\s+KEY-----', '[REDACTED: Private Key]'),
    (r'-----BEGIN\s+OPENSSH\s+PRIVATE\s+KEY-----[\s\S]*?-----END\s+OPENSSH\s+PRIVATE\s+KEY-----', '[REDACTED: SSH Private Key]'),
    (r'postgres://[^\s]+', '[REDACTED: Database URL]'),
    (r'mysql://[^\s]+', '[REDACTED: Database URL]'),
    (r'mongodb(\+srv)?://[^\s]+', '[REDACTED: MongoDB URL]'),
    (r'redis://[^\s]+', '[REDACTED: Redis URL]'),
    (r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}:[^\s@]+@', '[REDACTED: Credential in URL]'),
    (r'password\s*[=:]\s*["\']?[^\s"\']{8,}["\']?', '[REDACTED: Password]', re.IGNORECASE),
    (r'api[_-]?key\s*[=:]\s*["\']?[a-zA-Z0-9_-]{16,}["\']?', '[REDACTED: API Key]', re.IGNORECASE),
    (r'secret\s*[=:]\s*["\']?[a-zA-Z0-9_-]{16,}["\']?', '[REDACTED: Secret]', re.IGNORECASE),
    (r'token\s*[=:]\s*["\']?[a-zA-Z0-9_.-]{20,}["\']?', '[REDACTED: Token]', re.IGNORECASE),
    (r'supabase_[a-zA-Z0-9_-]{20,}', '[REDACTED: Supabase Key]'),
    (r'sb_[a-zA-Z0-9_-]{20,}', '[REDACTED: Supabase Key]'),
]

def redact_secrets(text):
    """Redact sensitive information from text."""
    if not text:
        return text
    
    for pattern in SECRET_PATTERNS:
        if len(pattern) == 3:
            regex, replacement, flags = pattern
            text = re.sub(regex, replacement, text, flags=flags)
        else:
            regex, replacement = pattern
            text = re.sub(regex, replacement, text)
    
    return text

def format_code_block(code, language=""):
    """Format code as markdown code block."""
    if not code:
        return ""
    lang = language.lower() if language else ""
    return f"\n```{lang}\n{code}\n```\n"

def extract_text_content(content_list):
    """Extract text from Claude's content array."""
    texts = []
    for item in content_list:
        if isinstance(item, dict):
            if item.get('type') == 'text':
                texts.append(item.get('text', ''))
            elif item.get('type') == 'tool_use':
                tool_name = item.get('name', 'tool')
                tool_input = item.get('input', {})
                texts.append(f"\n**🔧 Tool: {tool_name}**\n")
                if isinstance(tool_input, dict):
                    for k, v in tool_input.items():
                        if k in ['command', 'content', 'code']:
                            texts.append(format_code_block(str(v), 'bash' if k == 'command' else ''))
                        else:
                            texts.append(f"- **{k}**: `{v}`\n")
            elif item.get('type') == 'tool_result':
                result = item.get('content', '')
                if result:
                    texts.append(f"\n**📤 Result:**\n{format_code_block(str(result)[:2000])}")
        elif isinstance(item, str):
            texts.append(item)
    return '\n'.join(texts)

def parse_session(session_path):
    """Parse a Claude Code session JSONL file."""
    messages = []
    session_meta = {}
    
    try:
        with open(session_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    
                    # Extract session metadata
                    if 'sessionId' in entry and not session_meta:
                        session_meta = {
                            'session_id': entry.get('sessionId', ''),
                            'agent_id': entry.get('agentId', ''),
                            'cwd': entry.get('cwd', ''),
                            'version': entry.get('version', ''),
                            'git_branch': entry.get('gitBranch', ''),
                        }
                    
                    # Extract timestamp
                    timestamp = entry.get('timestamp', '')
                    if timestamp:
                        try:
                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            if 'date' not in session_meta:
                                session_meta['date'] = dt.strftime('%Y-%m-%d')
                                session_meta['time'] = dt.strftime('%H:%M')
                        except:
                            pass
                    
                    # Extract message
                    msg_type = entry.get('type', '')
                    message = entry.get('message', {})
                    
                    if msg_type == 'user':
                        # User message
                        content = entry.get('message', {})
                        if isinstance(content, dict):
                            text = content.get('content', '')
                            if isinstance(text, list):
                                text = extract_text_content(text)
                            elif isinstance(text, str):
                                pass
                            else:
                                text = str(text)
                        else:
                            text = str(content)
                        if text:
                            messages.append(('user', text))
                    
                    elif msg_type == 'assistant':
                        # Assistant message
                        content = message.get('content', [])
                        if isinstance(content, list):
                            text = extract_text_content(content)
                        else:
                            text = str(content)
                        if text:
                            messages.append(('assistant', text))
                    
                except json.JSONDecodeError:
                    continue
                    
    except Exception as e:
        print(f"Error reading {session_path}: {e}")
        return None, None
    
    return session_meta, messages

def session_to_markdown(session_meta, messages, source_file):
    """Convert session to markdown format."""
    if not messages:
        return None
    
    date = session_meta.get('date', 'unknown')
    time = session_meta.get('time', '00:00')
    session_id = session_meta.get('session_id', '')[:8] or session_meta.get('agent_id', '')[:8]
    cwd = session_meta.get('cwd', '')
    version = session_meta.get('version', '')
    
    # Build frontmatter
    frontmatter = f"""---
type: claude-code-session
date: {date}
time: "{time}"
session_id: "{session_id}"
working_dir: "{cwd}"
cli_version: "{version}"
tags:
  - claude-code
  - ai-session
  - coding
---
"""

    # Build content
    content = f"""# 🤖 Claude Code Session — {date} {time.replace(':', '')}

| Property | Value |
|----------|-------|
| **Date** | {date} {time} |
| **Session ID** | `{session_id}` |
| **Working Dir** | `{cwd}` |
| **CLI Version** | {version} |

---
"""

    for role, text in messages:
        text = redact_secrets(text)
        if role == 'user':
            content += f"\n## 👤 User\n\n{text}\n\n---\n"
        else:
            content += f"\n## 🤖 Claude\n\n{text}\n\n---\n"
    
    content += "\n---\n*Session exported from Claude Code — secrets redacted*\n"
    
    return frontmatter + content

def main():
    """Main sync function."""
    print("🔄 Syncing Claude Code sessions to Obsidian...")
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Find all session files
    session_files = list(CLAUDE_PROJECTS_DIR.rglob("*.jsonl"))
    print(f"📁 Found {len(session_files)} session files")
    
    synced = 0
    skipped = 0
    
    for session_path in session_files:
        # Skip empty files
        if session_path.stat().st_size == 0:
            skipped += 1
            continue
        
        session_meta, messages = parse_session(session_path)
        
        if not messages:
            skipped += 1
            continue
        
        # Generate filename
        date = session_meta.get('date', 'unknown')
        time = session_meta.get('time', '0000').replace(':', '')
        session_id = session_meta.get('session_id', '')[:8] or session_meta.get('agent_id', '')[:8]
        
        filename = f"claude-code-{date}-{time}-{session_id}.md"
        output_path = OUTPUT_DIR / filename
        
        # Check if already synced
        if output_path.exists():
            skipped += 1
            continue
        
        # Generate markdown
        markdown = session_to_markdown(session_meta, messages, session_path)
        
        if not markdown:
            skipped += 1
            continue
        
        # Write file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown)
        
        synced += 1
        print(f"  ✅ {filename}")
    
    print(f"\n✅ Synced {synced} new sessions ({skipped} skipped)")
    print(f"📂 Output: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
