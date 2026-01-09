"""
Parser for GitHub Copilot Chat sessions.
Sessions stored in VS Code globalStorage.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from .base import BaseParser
from ..models import Session, Message, Provider, MessageRole


class CopilotParser(BaseParser):
    """Parser for GitHub Copilot Chat sessions."""
    
    provider = Provider.COPILOT
    
    def get_session_paths(self) -> List[Path]:
        """Get all Copilot Chat session files."""
        paths = []
        
        # Check VS Code globalStorage
        storage = self.get_vscode_global_storage()
        
        # Copilot Chat extension ID
        copilot_dir = storage / "github.copilot-chat"
        
        if copilot_dir.exists():
            # Conversations are stored in conversations directory
            convos_dir = copilot_dir / "conversations"
            if convos_dir.exists():
                paths.extend(convos_dir.glob("*.json"))
            
            # Also check for history
            history = copilot_dir / "history.json"
            if history.exists():
                paths.append(history)
        
        # Also check Cursor's Copilot extension
        cursor_storage = self.get_cursor_global_storage()
        copilot_cursor = cursor_storage / "github.copilot-chat"
        
        if copilot_cursor.exists():
            convos_dir = copilot_cursor / "conversations"
            if convos_dir.exists():
                paths.extend(convos_dir.glob("*.json"))
        
        return paths
    
    def parse_session(self, path: Path) -> Optional[Session]:
        """Parse Copilot Chat session file."""
        try:
            content = path.read_text(encoding='utf-8')
            data = json.loads(content)
        except Exception:
            return None
        
        messages: List[Message] = []
        
        # Handle different formats
        if isinstance(data, list):
            for item in data:
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
            created_at=datetime.fromtimestamp(path.stat().st_mtime),
            model="copilot",
            source_file=str(path),
            source_mtime=path.stat().st_mtime,
            tags=['copilot', 'github', 'ai-session', 'coding']
        )
    
    def _extract_messages(self, data: dict, messages: List[Message]) -> None:
        """Extract messages from conversation data."""
        # Copilot stores in 'turns' or 'messages'
        turns = data.get('turns', data.get('messages', data.get('conversation', [])))
        
        for turn in turns:
            if isinstance(turn, dict):
                # Handle request/response format
                request = turn.get('request', turn.get('userMessage', ''))
                response = turn.get('response', turn.get('assistantMessage', ''))
                
                if request:
                    messages.append(Message(
                        role=MessageRole.USER,
                        content=request if isinstance(request, str) else str(request)
                    ))
                
                if response:
                    messages.append(Message(
                        role=MessageRole.ASSISTANT,
                        content=response if isinstance(response, str) else str(response)
                    ))
                
                # Also handle role-based format
                role = turn.get('role', '').lower()
                content = turn.get('content', turn.get('text', ''))
                
                if role == 'user' and content and not request:
                    messages.append(Message(
                        role=MessageRole.USER,
                        content=content
                    ))
                elif role == 'assistant' and content and not response:
                    messages.append(Message(
                        role=MessageRole.ASSISTANT,
                        content=content
                    ))
