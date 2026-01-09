"""
Parser for Cursor IDE sessions.
Sessions stored in Cursor's globalStorage.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any

from .base import BaseParser
from ..models import Session, Message, Provider, MessageRole


class CursorParser(BaseParser):
    """Parser for Cursor IDE sessions."""
    
    provider = Provider.CURSOR
    
    def get_session_paths(self) -> List[Path]:
        """Get all Cursor session directories."""
        storage = self.get_cursor_global_storage()
        projects_dir = storage / "anysphere.cursor-chat"
        
        if not projects_dir.exists():
            return []
        
        paths = []
        for project_dir in projects_dir.iterdir():
            if project_dir.is_dir():
                # Look for conversation files
                for conv_file in project_dir.glob("*.json"):
                    paths.append(conv_file)
        
        return paths
    
    def parse_session(self, path: Path) -> Optional[Session]:
        """Parse a Cursor session from JSON file."""
        try:
            content = path.read_text(encoding='utf-8')
            data = json.loads(content)
        except Exception:
            return None
        
        if not isinstance(data, dict):
            return None
        
        # Extract messages
        messages: List[Message] = []
        raw_messages = data.get('messages', data.get('conversation', []))
        
        if not raw_messages:
            return None
        
        for msg in raw_messages:
            if isinstance(msg, dict):
                role = msg.get('role', '').lower()
                content = msg.get('content', msg.get('text', ''))
                
                if role == 'user' and content:
                    messages.append(Message(
                        role=MessageRole.USER,
                        content=content
                    ))
                elif role in ('assistant', 'ai') and content:
                    messages.append(Message(
                        role=MessageRole.ASSISTANT,
                        content=content
                    ))
        
        if not messages:
            return None
        
        # Extract metadata
        session_id = data.get('id', path.stem[:8])
        created_at = None
        
        if data.get('createdAt'):
            try:
                created_at = datetime.fromisoformat(str(data['createdAt']).replace('Z', '+00:00'))
            except:
                pass
        
        if not created_at:
            # Use birthtime for stable filenames
            created_at = self.get_file_created_at(path)
        
        return Session(
            id=str(session_id)[:8],
            provider=self.provider,
            messages=messages,
            created_at=created_at,
            model=data.get('model', ''),
            source_file=str(path),
            source_mtime=path.stat().st_mtime,
            tags=['cursor', 'ai-session', 'coding']
        )
