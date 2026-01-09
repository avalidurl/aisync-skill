#!/usr/bin/env python3
"""
Sync Codex CLI sessions to Obsidian as markdown notes.
Includes secret redaction for security.
Uses kebab-case for all filenames.
"""

import json
import os
import re
from pathlib import Path
from datetime import datetime

# Paths
CODEX_SESSIONS_DIR = Path.home() / ".codex" / "sessions"
OBSIDIAN_VAULT = Path.home() / "Library/Mobile Documents/iCloud~md~obsidian/Documents/zettelkasten"
OUTPUT_DIR = OBSIDIAN_VAULT / "ai-sessions" / "codex-sessions"

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

def to_kebab_case(text):
    """Convert text to kebab-case."""
    # Replace spaces and underscores with hyphens
    text = re.sub(r'[\s_]+', '-', text)
    # Convert to lowercase
    text = text.lower()
    # Remove any characters that aren't alphanumeric or hyphens
    text = re.sub(r'[^a-z0-9-]', '', text)
    # Remove multiple consecutive hyphens
    text = re.sub(r'-+', '-', text)
    # Remove leading/trailing hyphens
    text = text.strip('-')
    return text

def parse_session(session_path):
    """Parse a Codex session JSONL file."""
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
                    event_type = entry.get('type', '')
                    
                    if event_type == 'session_meta':
                        # Extract metadata from payload
                        payload = entry.get('payload', {})
                        session_meta = {
                            'session_id': payload.get('id', ''),
                            'started_at': payload.get('timestamp', ''),
                            'cwd': payload.get('cwd', ''),
                            'cli_version': payload.get('cli_version', ''),
                        }
                    elif event_type == 'response_item':
                        payload = entry.get('payload', {})
                        role = payload.get('role', '')
                        content = payload.get('content', [])
                        
                        if isinstance(content, list):
                            for item in content:
                                if isinstance(item, dict):
                                    item_type = item.get('type', '')
                                    text = item.get('text', '')
                                    
                                    # Skip system/instruction messages
                                    if item_type == 'input_text' and text:
                                        # Skip AGENTS.md and environment_context
                                        if text.startswith('# AGENTS.md') or text.startswith('<environment_context'):
                                            continue
                                        messages.append(('user', text))
                                    elif item_type == 'text' and text:
                                        messages.append(('assistant', text))
                                    elif item_type == 'tool_use':
                                        tool_name = item.get('name', 'tool')
                                        tool_input = item.get('input', {})
                                        tool_text = f"**🔧 Tool: {tool_name}**\n"
                                        if isinstance(tool_input, dict):
                                            for k, v in tool_input.items():
                                                if k in ['command', 'content']:
                                                    tool_text += format_code_block(str(v)[:500], 'bash' if k == 'command' else '')
                                                else:
                                                    tool_text += f"- **{k}**: `{str(v)[:200]}`\n"
                                        messages.append(('tool', tool_text))
                                    elif item_type == 'tool_result':
                                        output = item.get('output', '')
                                        if output:
                                            messages.append(('result', f"**📤 Result:**\n{format_code_block(str(output)[:1000])}"))
                                elif isinstance(item, str):
                                    messages.append((role or 'unknown', item))
                    elif event_type == 'event_msg':
                        # Handle user messages from event_msg type
                        payload = entry.get('payload', {})
                        if payload.get('type') == 'user_message':
                            msg = payload.get('message', '')
                            if msg and not msg.startswith('#') and not msg.startswith('<'):
                                messages.append(('user', msg))
                                    
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
    
    # Extract metadata
    started = session_meta.get('started_at', '')
    if started:
        try:
            dt = datetime.fromisoformat(started.replace('Z', '+00:00'))
            date = dt.strftime('%Y-%m-%d')
            time = dt.strftime('%H:%M')
        except:
            date = 'unknown'
            time = '00:00'
    else:
        date = 'unknown'
        time = '00:00'
    
    session_id = session_meta.get('session_id', source_file.stem)[:8]
    cwd = session_meta.get('cwd', '')
    cli_version = session_meta.get('cli_version', '')
    
    # Get first user message as summary
    first_user = next((m[1][:50] for m in messages if m[0] == 'user'), 'Session')
    
    # Build frontmatter
    frontmatter = f"""---
type: codex-session
date: {date}
time: "{time}"
session_id: "{session_id}"
working_dir: "{cwd}"
cli_version: "{cli_version}"
tags:
  - codex
  - ai-session
  - coding
summary: "{first_user}..."
---
"""

    # Build content
    content = f"""# 🤖 Codex Session — {date} {time.replace(':', '')}

| Property | Value |
|----------|-------|
| **Date** | {date} {time} |
| **Session ID** | `{session_id}` |
| **Working Dir** | `{cwd}` |
| **CLI Version** | {cli_version} |

---
"""

    for role, text in messages:
        text = redact_secrets(text)
        if role == 'user':
            content += f"\n## 👤 User\n\n{text}\n\n---\n"
        elif role == 'assistant':
            content += f"\n## 🤖 Codex\n\n{text}\n\n---\n"
        elif role in ('tool', 'result'):
            content += f"\n{text}\n"
    
    content += "\n---\n*Session exported from Codex CLI — secrets redacted*\n"
    
    return frontmatter + content

def main():
    """Main sync function."""
    print("🔄 Syncing Codex sessions to Obsidian...")
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Find all session files
    if not CODEX_SESSIONS_DIR.exists():
        print(f"❌ Codex sessions directory not found: {CODEX_SESSIONS_DIR}")
        return
    
    session_files = list(CODEX_SESSIONS_DIR.rglob("*.jsonl"))
    print(f"📁 Found {len(session_files)} session files")
    
    synced = 0
    skipped = 0
    
    for session_path in session_files:
        session_meta, messages = parse_session(session_path)
        
        if not messages:
            skipped += 1
            continue
        
        # Generate kebab-case filename
        started = session_meta.get('started_at', '')
        if started:
            try:
                dt = datetime.fromisoformat(started.replace('Z', '+00:00'))
                date = dt.strftime('%Y-%m-%d')
                time = dt.strftime('%H%M')
            except:
                date = 'unknown'
                time = '0000'
        else:
            date = 'unknown'
            time = '0000'
        
        session_id = session_meta.get('session_id', session_path.stem)[:8]
        filename = f"codex-{date}-{time}-{session_id}.md"
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
