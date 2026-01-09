"""
Parser for Windsurf (Codeium) sessions.
Sessions stored in Windsurf's application data.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional
import os

from .base import BaseParser
from ..models import Session, Message, Provider, MessageRole


class WindsurfParser(BaseParser):
    """Parser for Windsurf IDE sessions."""
    
    provider = Provider.WINDSURF
    
    def get_session_paths(self) -> List[Path]:
        """Get all Windsurf session files."""
        paths = []
        
        # Windsurf stores data similar to VS Code
        if self.system == "Darwin":
            windsurf_dir = self.home_dir / "Library/Application Support/Windsurf"
        elif self.system == "Linux":
            windsurf_dir = self.home_dir / ".config/Windsurf"
        else:
            appdata = Path(os.environ.get('APPDATA', self.home_dir / 'AppData/Roaming'))
            windsurf_dir = appdata / "Windsurf"
        
        if windsurf_dir.exists():
            # Check User/globalStorage
            global_storage = windsurf_dir / "User/globalStorage"
            if global_storage.exists():
                # Look for Codeium extension data
                codeium_dir = global_storage / "codeium.codeium"
                if codeium_dir.exists():
                    paths.extend(codeium_dir.glob("**/*.json"))
                
                # Also check for chat history
                for ext_dir in global_storage.iterdir():
                    if ext_dir.is_dir():
                        paths.extend(ext_dir.glob("**/conversation*.json"))
                        paths.extend(ext_dir.glob("**/history*.json"))
        
        return paths
    
    def parse_session(self, path: Path) -> Optional[Session]:
        """Parse Windsurf session file."""
        try:
            content = path.read_text(encoding='utf-8')
            data = json.loads(content)
        except Exception:
            return None
        
        messages: List[Message] = []
        
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    self._extract_messages(item, messages)
        elif isinstance(data, dict):
            self._extract_messages(data, messages)
        
        if not messages:
            return None
        
        session_id = path.stem[:8]
        
        return Session(
            id=session_id,
            provider=self.provider,
            messages=messages,
            created_at=self.get_file_created_at(path),
            model="windsurf",
            source_file=str(path),
            source_mtime=path.stat().st_mtime,
            tags=['windsurf', 'codeium', 'ai-session', 'coding']
        )
    
    def _extract_messages(self, data: dict, messages: List[Message]) -> None:
        """Extract messages from data."""
        # Try various message storage formats
        for key in ['messages', 'conversation', 'history', 'turns']:
            conversation = data.get(key, [])
            if conversation:
                break
        
        for msg in conversation:
            if isinstance(msg, dict):
                role = msg.get('role', msg.get('type', '')).lower()
                content = msg.get('content', msg.get('text', msg.get('message', '')))
                
                # Handle structured content
                if isinstance(content, list):
                    parts = [
                        item.get('text', str(item)) if isinstance(item, dict) else str(item)
                        for item in content
                    ]
                    content = '\n\n'.join(parts)
                
                if role in ('user', 'human') and content:
                    messages.append(Message(
                        role=MessageRole.USER,
                        content=content
                    ))
                elif role in ('assistant', 'ai', 'model') and content:
                    messages.append(Message(
                        role=MessageRole.ASSISTANT,
                        content=content
                    ))
