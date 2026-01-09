"""
Parser for Sourcegraph Amp sessions.
Sessions stored in ~/.amp/ or VS Code globalStorage.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from .base import BaseParser
from ..models import Session, Message, Provider, MessageRole


class AmpParser(BaseParser):
    """Parser for Sourcegraph Amp AI agent sessions."""
    
    provider = Provider.AMP
    
    def get_session_paths(self) -> List[Path]:
        """Get all Amp session files."""
        paths = []
        
        # Check ~/.amp/
        amp_dir = self.home_dir / ".amp"
        if amp_dir.exists():
            # Sessions directory
            sessions_dir = amp_dir / "sessions"
            if sessions_dir.exists():
                paths.extend(sessions_dir.glob("*.json"))
                paths.extend(sessions_dir.glob("*.jsonl"))
            
            # Conversations
            convos_dir = amp_dir / "conversations"
            if convos_dir.exists():
                paths.extend(convos_dir.glob("*.json"))
            
            # History
            history = amp_dir / "history.json"
            if history.exists():
                paths.append(history)
        
        # Also check VS Code extension
        storage = self.get_vscode_global_storage()
        
        # Sourcegraph extension
        sg_dir = storage / "sourcegraph.cody-ai"
        if sg_dir.exists():
            paths.extend(sg_dir.glob("**/conversation*.json"))
            paths.extend(sg_dir.glob("**/history*.json"))
        
        return paths
    
    def parse_session(self, path: Path) -> Optional[Session]:
        """Parse Amp session file."""
        # Handle JSONL
        if path.suffix == '.jsonl':
            return self._parse_jsonl(path)
        
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
                    if item.get('model') and not model:
                        model = item['model']
        elif isinstance(data, dict):
            model = data.get('model', '')
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
            tags=['amp', 'sourcegraph', 'ai-session', 'coding']
        )
    
    def _parse_jsonl(self, path: Path) -> Optional[Session]:
        """Parse JSONL session file."""
        try:
            content = path.read_text(encoding='utf-8')
        except Exception:
            return None
        
        messages: List[Message] = []
        model = ""
        
        for line in content.split('\n'):
            if line.strip():
                try:
                    entry = json.loads(line)
                    
                    if entry.get('model'):
                        model = entry['model']
                    
                    role = entry.get('role', '').lower()
                    msg_content = entry.get('content', entry.get('message', ''))
                    
                    if role == 'user' and msg_content:
                        messages.append(Message(
                            role=MessageRole.USER,
                            content=msg_content
                        ))
                    elif role in ('assistant', 'model') and msg_content:
                        messages.append(Message(
                            role=MessageRole.ASSISTANT,
                            content=msg_content
                        ))
                except:
                    continue
        
        if not messages:
            return None
        
        return Session(
            id=path.stem[:8],
            provider=self.provider,
            messages=messages,
            created_at=datetime.fromtimestamp(path.stat().st_mtime),
            model=model,
            source_file=str(path),
            source_mtime=path.stat().st_mtime,
            tags=['amp', 'sourcegraph', 'ai-session', 'coding']
        )
    
    def _extract_messages(self, data: dict, messages: List[Message]) -> None:
        """Extract messages from data."""
        # Try different message keys
        for key in ['messages', 'interactions', 'conversation', 'history']:
            conversation = data.get(key, [])
            if conversation:
                break
        
        for msg in conversation:
            if isinstance(msg, dict):
                # Handle humanMessage/assistantMessage format (Cody style)
                human = msg.get('humanMessage', {})
                assistant = msg.get('assistantMessage', {})
                
                if human:
                    text = human.get('text', human.get('content', ''))
                    if text:
                        messages.append(Message(
                            role=MessageRole.USER,
                            content=text
                        ))
                
                if assistant:
                    text = assistant.get('text', assistant.get('content', ''))
                    if text:
                        messages.append(Message(
                            role=MessageRole.ASSISTANT,
                            content=text
                        ))
                
                # Also handle standard role format
                role = msg.get('role', msg.get('speaker', '')).lower()
                content = msg.get('content', msg.get('text', msg.get('message', '')))
                
                # Handle content as array
                if isinstance(content, list):
                    parts = [
                        item.get('text', str(item)) if isinstance(item, dict) else str(item)
                        for item in content
                    ]
                    content = '\n\n'.join(parts)
                
                if role in ('user', 'human') and content and not human:
                    messages.append(Message(
                        role=MessageRole.USER,
                        content=content
                    ))
                elif role in ('assistant', 'ai', 'model') and content and not assistant:
                    messages.append(Message(
                        role=MessageRole.ASSISTANT,
                        content=content
                    ))
