"""
Parser for Continue.dev sessions.
Sessions stored in VS Code globalStorage or ~/.continue/
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from .base import BaseParser
from ..models import Session, Message, Provider, MessageRole


class ContinueParser(BaseParser):
    """Parser for Continue.dev VS Code extension sessions."""
    
    provider = Provider.CONTINUE
    
    def get_session_paths(self) -> List[Path]:
        """Get all Continue.dev session files."""
        paths = []
        
        # Check VS Code globalStorage
        storage = self.get_vscode_global_storage()
        continue_dir = storage / "continue.continue"
        
        if continue_dir.exists():
            # Sessions are in sessions/ directory
            sessions_dir = continue_dir / "sessions"
            if sessions_dir.exists():
                paths.extend(sessions_dir.glob("*.json"))
            
            # Also check for history.json
            history = continue_dir / "history.json"
            if history.exists():
                paths.append(history)
        
        # Also check ~/.continue/
        home_continue = self.home_dir / ".continue"
        if home_continue.exists():
            sessions_dir = home_continue / "sessions"
            if sessions_dir.exists():
                paths.extend(sessions_dir.glob("*.json"))
        
        return paths
    
    def parse_session(self, path: Path) -> Optional[Session]:
        """Parse Continue.dev session file."""
        try:
            content = path.read_text(encoding='utf-8')
            data = json.loads(content)
        except Exception:
            return None
        
        messages: List[Message] = []
        model = ""
        
        # Handle history.json (array of sessions)
        if isinstance(data, list):
            for item in data:
                self._extract_session_messages(item, messages)
                if item.get('model') and not model:
                    model = item['model']
        elif isinstance(data, dict):
            self._extract_session_messages(data, messages)
            model = data.get('model', '')
        
        if not messages:
            return None
        
        session_id = path.stem[:8]
        
        return Session(
            id=session_id,
            provider=self.provider,
            messages=messages,
            created_at=datetime.fromtimestamp(path.stat().st_mtime),
            model=model,
            source_file=str(path),
            source_mtime=path.stat().st_mtime,
            tags=['continue', 'ai-session', 'coding']
        )
    
    def _extract_session_messages(self, session: dict, messages: List[Message]) -> None:
        """Extract messages from session data."""
        # Continue stores messages in 'history' or 'messages'
        history = session.get('history', session.get('messages', []))
        
        for msg in history:
            if isinstance(msg, dict):
                role = msg.get('role', '').lower()
                content = msg.get('content', msg.get('message', ''))
                
                # Handle content as array
                if isinstance(content, list):
                    parts = []
                    for item in content:
                        if isinstance(item, str):
                            parts.append(item)
                        elif isinstance(item, dict):
                            text = item.get('text', item.get('content', ''))
                            if text:
                                parts.append(text)
                    content = '\n\n'.join(parts)
                
                if role == 'user' and content:
                    messages.append(Message(
                        role=MessageRole.USER,
                        content=content
                    ))
                elif role == 'assistant' and content:
                    messages.append(Message(
                        role=MessageRole.ASSISTANT,
                        content=content
                    ))
