"""
Parser for Aider sessions.
Sessions stored in project directories as .aider.chat.history.md
"""

import re
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from .base import BaseParser
from ..models import Session, Message, Provider, MessageRole


class AiderParser(BaseParser):
    """Parser for Aider chat history files."""
    
    provider = Provider.AIDER
    
    def get_session_paths(self) -> List[Path]:
        """Get all Aider history files."""
        # Check common locations
        paths = []
        
        # Home directory
        home_history = self.home_dir / ".aider.chat.history.md"
        if home_history.exists():
            paths.append(home_history)
        
        # Also check XDG config
        xdg_config = self.home_dir / ".config" / "aider"
        if xdg_config.exists():
            paths.extend(xdg_config.glob("*.md"))
        
        # Check for project-level history in common dev directories
        dev_dirs = [
            self.home_dir / "Projects",
            self.home_dir / "Development", 
            self.home_dir / "code",
            self.home_dir / "repos",
        ]
        
        for dev_dir in dev_dirs:
            if dev_dir.exists():
                paths.extend(dev_dir.rglob(".aider.chat.history.md"))
        
        return paths
    
    def parse_session(self, path: Path) -> Optional[Session]:
        """Parse Aider markdown history file."""
        try:
            content = path.read_text(encoding='utf-8')
        except Exception:
            return None
        
        if not content.strip():
            return None
        
        messages: List[Message] = []
        
        # Aider uses markdown format with #### headers
        # #### /ask What is this? (user)
        # Response... (assistant)
        
        # Split by user commands (#### lines starting with /)
        sections = re.split(r'^####\s+', content, flags=re.MULTILINE)
        
        for section in sections:
            if not section.strip():
                continue
            
            lines = section.split('\n', 1)
            header = lines[0].strip()
            body = lines[1].strip() if len(lines) > 1 else ''
            
            # User message (command line)
            if header.startswith('/'):
                messages.append(Message(
                    role=MessageRole.USER,
                    content=header
                ))
            elif header:
                # This is a user question without /
                messages.append(Message(
                    role=MessageRole.USER,
                    content=header
                ))
            
            # Assistant response
            if body:
                messages.append(Message(
                    role=MessageRole.ASSISTANT,
                    content=body
                ))
        
        if not messages:
            return None
        
        # Get session ID from parent directory name or filename
        session_id = path.parent.name[:8] if path.parent.name != str(self.home_dir) else "aider"
        
        return Session(
            id=session_id,
            provider=self.provider,
            messages=messages,
            created_at=datetime.fromtimestamp(path.stat().st_mtime),
            working_dir=str(path.parent),
            source_file=str(path),
            source_mtime=path.stat().st_mtime,
            tags=['aider', 'ai-session', 'coding']
        )
