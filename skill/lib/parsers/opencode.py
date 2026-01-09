"""
Parser for OpenCode AI sessions.
Sessions stored in:
- macOS/Linux: ~/.local/share/opencode/
- Windows: %USERPROFILE%\.local\share\opencode

Structure:
- project/<project-slug>/storage/ - Git project sessions
- global/storage/ - Non-git project sessions
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
import os

from .base import BaseParser
from ..models import Session, Message, Provider, MessageRole


class OpenCodeParser(BaseParser):
    """Parser for OpenCode AI sessions."""
    
    provider = Provider.OPENCODE
    
    def get_opencode_dir(self) -> Path:
        """Get OpenCode data directory for current platform."""
        if self.system == "Windows":
            return Path(os.environ.get('USERPROFILE', self.home_dir)) / ".local/share/opencode"
        else:
            # macOS and Linux
            return self.home_dir / ".local/share/opencode"
    
    def get_session_paths(self) -> List[Path]:
        """Get all OpenCode session files."""
        opencode_dir = self.get_opencode_dir()
        
        if not opencode_dir.exists():
            return []
        
        paths = []
        
        # Check project directory for Git project sessions
        project_dir = opencode_dir / "project"
        if project_dir.exists():
            # Look for storage directories within project slugs
            for project in project_dir.iterdir():
                if project.is_dir():
                    storage_dir = project / "storage"
                    if storage_dir.exists():
                        paths.extend(self.find_files(storage_dir, "*.json"))
                        paths.extend(self.find_files(storage_dir, "*.jsonl"))
        
        # Check global storage for non-Git sessions
        global_storage = opencode_dir / "global" / "storage"
        if global_storage.exists():
            paths.extend(self.find_files(global_storage, "*.json"))
            paths.extend(self.find_files(global_storage, "*.jsonl"))
        
        # Also check for session files directly in project dirs
        if project_dir.exists():
            for project in project_dir.iterdir():
                if project.is_dir():
                    paths.extend(self.find_files(project, "session*.json"))
                    paths.extend(self.find_files(project, "messages*.json"))
        
        return paths
    
    def parse_session(self, path: Path) -> Optional[Session]:
        """Parse an OpenCode session file."""
        try:
            content = path.read_text(encoding='utf-8')
        except Exception:
            return None
        
        messages: List[Message] = []
        model = ""
        working_dir = ""
        created_at = None
        
        # Try to extract project name from path
        project_name = ""
        parts = path.parts
        try:
            if "project" in parts:
                idx = parts.index("project")
                if idx + 1 < len(parts):
                    project_name = parts[idx + 1]
        except:
            pass
        
        # Handle JSONL format
        if path.suffix == '.jsonl':
            for line in content.split('\n'):
                if line.strip():
                    try:
                        entry = json.loads(line)
                        self._extract_message(entry, messages)
                        if entry.get('model'):
                            model = entry['model']
                        if entry.get('timestamp') and not created_at:
                            created_at = self._parse_timestamp(entry['timestamp'])
                    except json.JSONDecodeError:
                        pass
        else:
            # Handle JSON
            try:
                data = json.loads(content)
                
                # Handle various possible structures
                if isinstance(data, list):
                    for entry in data:
                        self._extract_message(entry, messages)
                        if entry.get('model'):
                            model = entry['model']
                elif isinstance(data, dict):
                    model = data.get('model', '')
                    working_dir = data.get('cwd', data.get('working_dir', ''))
                    
                    # Try different message array keys
                    conversation = (
                        data.get('messages', []) or
                        data.get('conversation', []) or
                        data.get('history', [])
                    )
                    
                    for msg in conversation:
                        self._extract_message(msg, messages)
                    
                    # Extract timestamp
                    if data.get('created_at'):
                        created_at = self._parse_timestamp(data['created_at'])
                    elif data.get('timestamp'):
                        created_at = self._parse_timestamp(data['timestamp'])
                    
            except json.JSONDecodeError:
                return None
        
        if not messages:
            return None
        
        session_id = path.stem[:8]
        
        if not created_at:
            created_at = datetime.fromtimestamp(path.stat().st_mtime)
        
        return Session(
            id=session_id,
            provider=self.provider,
            messages=messages,
            created_at=created_at,
            working_dir=working_dir,
            project_name=project_name,
            model=model,
            source_file=str(path),
            source_mtime=path.stat().st_mtime,
            tags=['opencode', 'ai-session', 'coding']
        )
    
    def _extract_message(self, entry: dict, messages: List[Message]) -> None:
        """Extract message from entry."""
        if not isinstance(entry, dict):
            return
        
        role = entry.get('role', '').lower()
        content = entry.get('content', entry.get('text', ''))
        
        # Handle content that might be a list (like OpenAI format)
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict) and item.get('text'):
                    parts.append(item['text'])
            content = '\n\n'.join(parts)
        
        if not content:
            return
        
        timestamp = None
        if entry.get('timestamp'):
            timestamp = self._parse_timestamp(entry['timestamp'])
        
        if role == 'user':
            messages.append(Message(
                role=MessageRole.USER,
                content=content,
                timestamp=timestamp
            ))
        elif role in ('assistant', 'model', 'ai'):
            messages.append(Message(
                role=MessageRole.ASSISTANT,
                content=content,
                timestamp=timestamp
            ))
        elif role == 'system':
            messages.append(Message(
                role=MessageRole.SYSTEM,
                content=content,
                timestamp=timestamp
            ))
        elif role == 'tool':
            messages.append(Message(
                role=MessageRole.TOOL,
                content=content,
                timestamp=timestamp,
                tool_name=entry.get('name', entry.get('tool_name'))
            ))
    
    def _parse_timestamp(self, ts: Any) -> Optional[datetime]:
        """Parse timestamp from various formats."""
        if not ts:
            return None
        
        try:
            if isinstance(ts, (int, float)):
                # Unix timestamp (might be ms or s)
                if ts > 1e12:
                    ts = ts / 1000
                return datetime.fromtimestamp(ts)
            elif isinstance(ts, str):
                # ISO format
                return datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except:
            pass
        
        return None
