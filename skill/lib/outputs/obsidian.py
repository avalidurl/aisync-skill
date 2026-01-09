"""
Obsidian output plugin.
Generates markdown files with YAML frontmatter.
"""

from pathlib import Path
from typing import Optional

from .base import BaseOutput
from ..models import Session, MessageRole
from ..redact import redact_secrets


class ObsidianOutput(BaseOutput):
    """Output sessions as Obsidian markdown notes."""
    
    name = "obsidian"
    description = "Markdown files with YAML frontmatter for Obsidian"
    
    def __init__(self, output_dir: Path, **config):
        super().__init__(output_dir, **config)
        self.redact = config.get('redact', True)
    
    def get_session_path(self, session: Session) -> Path:
        """Get output path for session."""
        folder = f"{session.provider.value}-sessions"
        filename = f"{self.get_session_filename(session)}.md"
        return self.output_dir / folder / filename
    
    def session_exists(self, session: Session) -> bool:
        """Check if session file exists."""
        return self.get_session_path(session).exists()
    
    def needs_update(self, session: Session) -> bool:
        """Check if session needs update based on mtime."""
        path = self.get_session_path(session)
        if not path.exists():
            return True
        
        if session.source_mtime:
            return session.source_mtime > path.stat().st_mtime
        
        return False
    
    def write_session(self, session: Session) -> bool:
        """Write session as markdown file."""
        path = self.get_session_path(session)
        self.ensure_dir(path.parent)
        
        # Delete if exists (for updates)
        if path.exists():
            path.unlink()
        
        markdown = self.generate_markdown(session)
        path.write_text(markdown, encoding='utf-8')
        return True
    
    def generate_markdown(self, session: Session) -> str:
        """Generate markdown content for session."""
        # YAML frontmatter
        tags_yaml = '\n'.join(f'  - {tag}' for tag in session.tags)
        summary = session.summary.replace('"', '\\"').replace('\n', ' ')
        
        md = f'''---
type: {session.provider.value}-session
date: {session.date_str}
time: "{session.time_str}"
session_id: "{session.id}"
'''
        
        if session.working_dir:
            md += f'working_dir: "{session.working_dir}"\n'
        
        if session.model:
            md += f'model: "{session.model}"\n'
        
        if session.project_name:
            md += f'project: "{session.project_name}"\n'
        
        md += f'''tags:
{tags_yaml}
summary: "{summary}"
'''
        
        # Analytics
        if session.total_tokens:
            md += f'total_tokens: {session.total_tokens}\n'
        if session.user_messages:
            md += f'user_messages: {session.user_messages}\n'
        if session.assistant_messages:
            md += f'assistant_messages: {session.assistant_messages}\n'
        if session.tool_calls:
            md += f'tool_calls: {session.tool_calls}\n'
        if session.languages:
            md += f'languages: [{", ".join(session.languages)}]\n'
        
        md += '---\n\n'
        
        # Header
        provider_emoji = self._get_provider_emoji(session.provider.value)
        provider_name = session.provider.value.replace('-', ' ').title()
        md += f'# {provider_emoji} {provider_name} Session — {session.date_str} {session.time_str.replace(":", "")}\n\n'
        
        # Metadata table
        md += '| Property | Value |\n'
        md += '|----------|-------|\n'
        md += f'| **Date** | {session.date_str} {session.time_str} |\n'
        md += f'| **Session ID** | `{session.id}` |\n'
        
        if session.working_dir:
            md += f'| **Working Dir** | `{session.working_dir}` |\n'
        if session.model:
            md += f'| **Model** | {session.model} |\n'
        if session.total_tokens:
            md += f'| **Tokens** | ~{session.total_tokens:,} |\n'
        
        md += '\n---\n\n'
        
        # Messages
        for msg in session.messages:
            content = redact_secrets(msg.content) if self.redact else msg.content
            
            if msg.role == MessageRole.USER:
                md += f'## 👤 User\n\n{content}\n\n---\n\n'
            elif msg.role == MessageRole.ASSISTANT:
                md += f'## {provider_emoji} {provider_name}\n\n{content}\n\n---\n\n'
            elif msg.role == MessageRole.TOOL:
                md += f'## 🔧 Tool: {msg.tool_name or "unknown"}\n\n{content}\n\n---\n\n'
        
        # Footer
        from datetime import datetime
        sync_time = datetime.now().isoformat()
        md += f'\n---\n*🔌 Synced at {sync_time} — secrets redacted*\n'
        
        return md
    
    def _get_provider_emoji(self, provider: str) -> str:
        """Get emoji for provider."""
        emojis = {
            'claude-code': '🤖',
            'codex': '🧠',
            'cursor': '📝',
            'aider': '🔧',
            'cline': '🤖',
            'gemini-cli': '💎',
            'continue': '🔄',
            'copilot': '🐙',
            'roo-code': '🦘',
            'windsurf': '🏄',
            'zed-ai': '⚡',
            'amp': '⚡',
        }
        return emojis.get(provider, '🤖')
