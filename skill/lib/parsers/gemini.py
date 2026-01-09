"""
Parser for Gemini CLI sessions.
Sessions stored in ~/.gemini/sessions/
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from .base import BaseParser
from ..models import Session, Message, Provider, MessageRole


class GeminiCLIParser(BaseParser):
    """Parser for Google Gemini CLI sessions."""
    
    provider = Provider.GEMINI_CLI
    
    def get_session_paths(self) -> List[Path]:
        """Get all Gemini CLI session files."""
        gemini_dir = self.home_dir / ".gemini"
        
        paths = []
        
        # Check sessions directory
        sessions_dir = gemini_dir / "sessions"
        if sessions_dir.exists():
            paths.extend(sessions_dir.glob("*.json"))
            paths.extend(sessions_dir.glob("*.jsonl"))
        
        # Also check history
        history_file = gemini_dir / "history.json"
        if history_file.exists():
            paths.append(history_file)
        
        return paths
    
    def parse_session(self, path: Path) -> Optional[Session]:
        """Parse Gemini CLI session file."""
        try:
            content = path.read_text(encoding='utf-8')
        except Exception:
            return None
        
        messages: List[Message] = []
        model = ""
        
        # Handle JSONL
        if path.suffix == '.jsonl':
            for line in content.split('\n'):
                if line.strip():
                    try:
                        entry = json.loads(line)
                        self._extract_message(entry, messages)
                        if entry.get('model'):
                            model = entry['model']
                    except:
                        pass
        else:
            # Handle JSON
            try:
                data = json.loads(content)
                
                if isinstance(data, list):
                    for entry in data:
                        self._extract_message(entry, messages)
                elif isinstance(data, dict):
                    model = data.get('model', '')
                    conversation = data.get('contents', data.get('messages', []))
                    for msg in conversation:
                        self._extract_message(msg, messages)
            except:
                return None
        
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
            tags=['gemini', 'google', 'ai-session', 'coding']
        )
    
    def _extract_message(self, entry: dict, messages: List[Message]) -> None:
        """Extract message from entry."""
        role = entry.get('role', '').lower()
        
        # Handle Gemini's parts structure
        parts = entry.get('parts', [])
        if parts:
            content = '\n\n'.join(
                p.get('text', str(p)) if isinstance(p, dict) else str(p)
                for p in parts
            )
        else:
            content = entry.get('content', entry.get('text', ''))
        
        if role == 'user' and content:
            messages.append(Message(
                role=MessageRole.USER,
                content=content
            ))
        elif role in ('model', 'assistant') and content:
            messages.append(Message(
                role=MessageRole.ASSISTANT,
                content=content
            ))
