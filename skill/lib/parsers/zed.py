"""
Parser for Zed AI sessions.
Sessions stored in Zed's application data.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from .base import BaseParser
from ..models import Session, Message, Provider, MessageRole


class ZedAIParser(BaseParser):
    """Parser for Zed editor AI assistant sessions."""
    
    provider = Provider.ZED_AI
    
    def get_session_paths(self) -> List[Path]:
        """Get all Zed AI session files."""
        paths = []
        
        # Zed stores data in different locations per platform
        if self.system == "Darwin":
            zed_dir = self.home_dir / "Library/Application Support/Zed"
        elif self.system == "Linux":
            zed_dir = self.home_dir / ".config/zed"
        else:
            zed_dir = self.home_dir / ".zed"
        
        if zed_dir.exists():
            # Check for conversation history
            convos_dir = zed_dir / "conversations"
            if convos_dir.exists():
                paths.extend(convos_dir.glob("*.json"))
                paths.extend(convos_dir.glob("*.md"))
            
            # Also check for assistant data
            assistant_dir = zed_dir / "assistant"
            if assistant_dir.exists():
                paths.extend(assistant_dir.glob("**/*.json"))
            
            # Check for saved prompts/conversations
            prompts_dir = zed_dir / "prompts"
            if prompts_dir.exists():
                paths.extend(prompts_dir.glob("*.json"))
        
        return paths
    
    def parse_session(self, path: Path) -> Optional[Session]:
        """Parse Zed AI session file."""
        # Handle markdown files
        if path.suffix == '.md':
            return self._parse_markdown(path)
        
        try:
            content = path.read_text(encoding='utf-8')
            data = json.loads(content)
        except Exception:
            return None
        
        messages: List[Message] = []
        model = ""
        
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    self._extract_messages(item, messages)
        elif isinstance(data, dict):
            model = data.get('model', data.get('provider', ''))
            self._extract_messages(data, messages)
        
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
            tags=['zed', 'ai-session', 'coding']
        )
    
    def _parse_markdown(self, path: Path) -> Optional[Session]:
        """Parse markdown conversation file."""
        import re
        
        try:
            content = path.read_text(encoding='utf-8')
        except Exception:
            return None
        
        messages: List[Message] = []
        
        # Zed uses markdown headers for messages
        # ## User / ## Assistant format
        sections = re.split(r'^##\s+', content, flags=re.MULTILINE)
        
        for section in sections:
            if not section.strip():
                continue
            
            lines = section.split('\n', 1)
            header = lines[0].strip().lower()
            body = lines[1].strip() if len(lines) > 1 else ''
            
            if 'user' in header and body:
                messages.append(Message(
                    role=MessageRole.USER,
                    content=body
                ))
            elif ('assistant' in header or 'ai' in header) and body:
                messages.append(Message(
                    role=MessageRole.ASSISTANT,
                    content=body
                ))
        
        if not messages:
            return None
        
        return Session(
            id=path.stem[:8],
            provider=self.provider,
            messages=messages,
            created_at=datetime.fromtimestamp(path.stat().st_mtime),
            source_file=str(path),
            source_mtime=path.stat().st_mtime,
            tags=['zed', 'ai-session', 'coding']
        )
    
    def _extract_messages(self, data: dict, messages: List[Message]) -> None:
        """Extract messages from data."""
        conversation = data.get('messages', data.get('conversation', data.get('history', [])))
        
        for msg in conversation:
            if isinstance(msg, dict):
                role = msg.get('role', '').lower()
                content = msg.get('content', msg.get('text', msg.get('body', '')))
                
                # Handle content blocks
                if isinstance(content, list):
                    parts = [
                        item.get('text', str(item)) if isinstance(item, dict) else str(item)
                        for item in content
                    ]
                    content = '\n\n'.join(parts)
                
                if role == 'user' and content:
                    messages.append(Message(
                        role=MessageRole.USER,
                        content=content
                    ))
                elif role in ('assistant', 'model') and content:
                    messages.append(Message(
                        role=MessageRole.ASSISTANT,
                        content=content
                    ))
