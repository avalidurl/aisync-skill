"""
Parser for Claude Code sessions.
Sessions stored in ~/.claude/projects/**/*.jsonl
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any

from .base import BaseParser
from ..models import Session, Message, Provider, MessageRole


class ClaudeCodeParser(BaseParser):
    """Parser for Claude Code CLI sessions."""
    
    provider = Provider.CLAUDE_CODE
    
    def get_session_paths(self) -> List[Path]:
        """Get all Claude Code session files."""
        claude_dir = self.home_dir / ".claude" / "projects"
        return self.find_files(claude_dir, "*.jsonl")
    
    def parse_session(self, path: Path) -> Optional[Session]:
        """Parse a Claude Code session from JSONL file."""
        try:
            content = path.read_text(encoding='utf-8')
        except Exception:
            return None
        
        lines = [l for l in content.split('\n') if l.strip()]
        if not lines:
            return None
        
        # Parse metadata and messages
        session_id = path.stem[:8]
        created_at = None
        working_dir = ""
        model = ""
        messages: List[Message] = []
        
        for line in lines:
            try:
                entry = json.loads(line)
                entry_type = entry.get('type', '')
                
                # Extract metadata
                if entry.get('sessionId') and not created_at:
                    session_id = str(entry['sessionId'])[:8]
                
                if entry.get('timestamp') and not created_at:
                    try:
                        created_at = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                    except:
                        pass
                
                if entry.get('cwd'):
                    working_dir = entry['cwd']
                
                if entry.get('model'):
                    model = entry['model']
                
                # Extract messages
                msg_content = entry.get('message', {}).get('content')
                
                if entry_type == 'user' and msg_content:
                    text = self._extract_text(msg_content)
                    if text and not text.startswith('<environment_context'):
                        messages.append(Message(
                            role=MessageRole.USER,
                            content=text
                        ))
                
                elif entry_type == 'assistant' and msg_content:
                    text = self._extract_text(msg_content)
                    if text:
                        messages.append(Message(
                            role=MessageRole.ASSISTANT,
                            content=text
                        ))
                        
            except json.JSONDecodeError:
                continue
        
        if not messages:
            return None
        
        if not created_at:
            created_at = datetime.fromtimestamp(path.stat().st_mtime)
        
        return Session(
            id=session_id,
            provider=self.provider,
            messages=messages,
            created_at=created_at,
            working_dir=working_dir,
            model=model,
            source_file=str(path),
            source_mtime=path.stat().st_mtime,
            tags=['claude-code', 'ai-session', 'coding']
        )
    
    def _extract_text(self, content: Any) -> str:
        """Extract text from content (string or array)."""
        if isinstance(content, str):
            return content
        
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    if item.get('type') == 'text' and item.get('text'):
                        parts.append(item['text'])
                    elif item.get('type') == 'tool_use':
                        tool_name = item.get('name', 'tool')
                        parts.append(f"**🔧 Tool: {tool_name}**")
                        if item.get('input'):
                            input_str = json.dumps(item['input'], indent=2)[:500] if isinstance(item['input'], dict) else str(item['input'])[:500]
                            parts.append(f"```\n{input_str}\n```")
                    elif item.get('type') == 'tool_result' and item.get('content'):
                        result = str(item['content'])[:1000]
                        parts.append(f"**📤 Result:**\n```\n{result}\n```")
            return '\n\n'.join(parts)
        
        return ''
