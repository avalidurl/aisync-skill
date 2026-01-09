"""
Parser for Roo Code sessions.
Sessions stored in VS Code globalStorage.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from .base import BaseParser
from ..models import Session, Message, Provider, MessageRole


class RooCodeParser(BaseParser):
    """Parser for Roo Code VS Code extension sessions."""
    
    provider = Provider.ROO_CODE
    
    def get_session_paths(self) -> List[Path]:
        """Get all Roo Code session files."""
        paths = []
        
        # Check VS Code globalStorage
        storage = self.get_vscode_global_storage()
        
        # Roo Code extension
        roo_dir = storage / "rooveterinaryinc.roo-cline"
        
        if roo_dir.exists():
            # Tasks directory
            tasks_dir = roo_dir / "tasks"
            if tasks_dir.exists():
                # Look for task JSON files
                paths.extend(tasks_dir.glob("*/conversation.json"))
                paths.extend(tasks_dir.glob("*/messages.json"))
            
            # History file
            history = roo_dir / "history.json"
            if history.exists():
                paths.append(history)
        
        # Also check ~/.roo-code/
        home_roo = self.home_dir / ".roo-code"
        if home_roo.exists():
            paths.extend(home_roo.glob("**/*.json"))
        
        return paths
    
    def parse_session(self, path: Path) -> Optional[Session]:
        """Parse Roo Code session file."""
        try:
            content = path.read_text(encoding='utf-8')
            data = json.loads(content)
        except Exception:
            return None
        
        messages: List[Message] = []
        
        if isinstance(data, list):
            for item in data:
                self._extract_messages(item, messages)
        elif isinstance(data, dict):
            self._extract_messages(data, messages)
        
        if not messages:
            return None
        
        session_id = path.parent.name[:8] if path.name in ['conversation.json', 'messages.json'] else path.stem[:8]
        
        return Session(
            id=session_id,
            provider=self.provider,
            messages=messages,
            created_at=datetime.fromtimestamp(path.stat().st_mtime),
            source_file=str(path),
            source_mtime=path.stat().st_mtime,
            tags=['roo-code', 'ai-session', 'coding']
        )
    
    def _extract_messages(self, data: dict, messages: List[Message]) -> None:
        """Extract messages from data."""
        conversation = data.get('messages', data.get('conversation', []))
        
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
