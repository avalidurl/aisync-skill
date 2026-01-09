"""
Parser for OpenAI Codex CLI sessions.
Sessions stored in ~/.codex/sessions/*.jsonl
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from .base import BaseParser
from ..models import Session, Message, Provider, MessageRole


class CodexParser(BaseParser):
    """Parser for Codex CLI sessions."""
    
    provider = Provider.CODEX
    
    def get_session_paths(self) -> List[Path]:
        """Get all Codex session files."""
        codex_dir = self.home_dir / ".codex" / "sessions"
        return self.find_files(codex_dir, "*.jsonl")
    
    def parse_session(self, path: Path) -> Optional[Session]:
        """Parse a Codex session from JSONL file."""
        try:
            content = path.read_text(encoding='utf-8')
        except Exception:
            return None
        
        lines = [l for l in content.split('\n') if l.strip()]
        if not lines:
            return None
        
        session_id = path.stem[:8]
        created_at = None
        model = ""
        messages: List[Message] = []
        
        for line in lines:
            try:
                entry = json.loads(line)
                
                if entry.get('timestamp') and not created_at:
                    try:
                        created_at = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                    except:
                        pass
                
                if entry.get('model'):
                    model = entry['model']
                
                role = entry.get('role', '')
                content = entry.get('content', '')
                
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
            model=model,
            source_file=str(path),
            source_mtime=path.stat().st_mtime,
            tags=['codex', 'ai-session', 'coding']
        )
