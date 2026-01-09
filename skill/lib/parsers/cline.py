"""
Parser for Cline (Claude Dev) sessions.
Sessions stored in VS Code globalStorage.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from .base import BaseParser
from ..models import Session, Message, Provider, MessageRole


class ClineParser(BaseParser):
    """Parser for Cline VS Code extension sessions."""
    
    provider = Provider.CLINE
    
    def get_session_paths(self) -> List[Path]:
        """Get all Cline session files."""
        storage = self.get_vscode_global_storage()
        
        # Cline stores data in saoudrizwan.claude-dev
        cline_dir = storage / "saoudrizwan.claude-dev"
        
        if not cline_dir.exists():
            return []
        
        # Look for task history
        tasks_file = cline_dir / "tasks" / "tasks.json"
        if tasks_file.exists():
            return [tasks_file]
        
        # Also check for individual task directories
        return list(cline_dir.glob("tasks/*/conversation.json"))
    
    def parse_session(self, path: Path) -> Optional[Session]:
        """Parse Cline session files."""
        try:
            content = path.read_text(encoding='utf-8')
            data = json.loads(content)
        except Exception:
            return None
        
        messages: List[Message] = []
        
        # Handle tasks.json (list of tasks)
        if isinstance(data, list):
            for task in data:
                self._extract_messages(task, messages)
        elif isinstance(data, dict):
            self._extract_messages(data, messages)
        
        if not messages:
            return None
        
        session_id = path.parent.name[:8] if path.name != "tasks.json" else "cline"
        
        return Session(
            id=session_id,
            provider=self.provider,
            messages=messages,
            created_at=datetime.fromtimestamp(path.stat().st_mtime),
            source_file=str(path),
            source_mtime=path.stat().st_mtime,
            tags=['cline', 'claude-dev', 'ai-session', 'coding']
        )
    
    def _extract_messages(self, task: dict, messages: List[Message]) -> None:
        """Extract messages from task data."""
        # Cline stores conversation in 'messages' or 'conversation'
        conversation = task.get('messages', task.get('conversation', []))
        
        for msg in conversation:
            if isinstance(msg, dict):
                role = msg.get('role', '').lower()
                content = msg.get('content', msg.get('text', ''))
                
                # Handle content array
                if isinstance(content, list):
                    parts = []
                    for item in content:
                        if isinstance(item, str):
                            parts.append(item)
                        elif isinstance(item, dict) and item.get('text'):
                            parts.append(item['text'])
                    content = '\n\n'.join(parts)
                
                if role in ('user', 'human') and content:
                    messages.append(Message(
                        role=MessageRole.USER,
                        content=content
                    ))
                elif role in ('assistant', 'ai') and content:
                    messages.append(Message(
                        role=MessageRole.ASSISTANT,
                        content=content
                    ))
