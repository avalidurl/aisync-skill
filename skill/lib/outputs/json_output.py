"""
JSON output plugin.
Exports sessions as JSON files or a single JSON database.
"""

import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from .base import BaseOutput
from ..models import Session
from ..redact import redact_secrets


class JSONOutput(BaseOutput):
    """Output sessions as JSON files."""
    
    name = "json"
    description = "JSON files for programmatic access"
    
    def __init__(self, output_dir: Path, **config):
        super().__init__(output_dir, **config)
        self.redact = config.get('redact', True)
        self.single_file = config.get('single_file', False)  # Combine all into one file
        self.pretty = config.get('pretty', True)
        self._sessions_cache: List[dict] = []
    
    def get_session_path(self, session: Session) -> Path:
        """Get output path for session."""
        if self.single_file:
            return self.output_dir / "sessions.json"
        
        folder = f"{session.provider.value}-sessions"
        filename = f"{self.get_session_filename(session)}.json"
        return self.output_dir / folder / filename
    
    def session_exists(self, session: Session) -> bool:
        """Check if session exists."""
        if self.single_file:
            # Check in sessions.json
            db_path = self.output_dir / "sessions.json"
            if not db_path.exists():
                return False
            try:
                data = json.loads(db_path.read_text())
                return any(s.get('id') == session.id for s in data.get('sessions', []))
            except:
                return False
        
        return self.get_session_path(session).exists()
    
    def needs_update(self, session: Session) -> bool:
        """Check if session needs update."""
        if self.single_file:
            db_path = self.output_dir / "sessions.json"
            if not db_path.exists():
                return True
            
            try:
                data = json.loads(db_path.read_text())
                for s in data.get('sessions', []):
                    if s.get('id') == session.id:
                        existing_mtime = s.get('source_mtime', 0)
                        return (session.source_mtime or 0) > existing_mtime
            except:
                return True
            return True
        
        path = self.get_session_path(session)
        if not path.exists():
            return True
        
        if session.source_mtime:
            return session.source_mtime > path.stat().st_mtime
        
        return False
    
    def write_session(self, session: Session) -> bool:
        """Write session as JSON."""
        # Redact if enabled
        if self.redact:
            for msg in session.messages:
                msg.content = redact_secrets(msg.content)
        
        session_dict = session.to_dict()
        
        if self.single_file:
            self._sessions_cache.append(session_dict)
            return True
        
        path = self.get_session_path(session)
        self.ensure_dir(path.parent)
        
        indent = 2 if self.pretty else None
        path.write_text(json.dumps(session_dict, indent=indent, default=str), encoding='utf-8')
        return True
    
    def finalize(self) -> None:
        """Finalize output (for single_file mode)."""
        if self.single_file and self._sessions_cache:
            self.ensure_dir(self.output_dir)
            db_path = self.output_dir / "sessions.json"
            
            # Load existing
            existing_sessions = []
            if db_path.exists():
                try:
                    data = json.loads(db_path.read_text())
                    existing_sessions = data.get('sessions', [])
                except:
                    pass
            
            # Merge (update existing, add new)
            existing_ids = {s.get('id') for s in existing_sessions}
            for new_session in self._sessions_cache:
                if new_session.get('id') in existing_ids:
                    # Update existing
                    existing_sessions = [
                        new_session if s.get('id') == new_session.get('id') else s
                        for s in existing_sessions
                    ]
                else:
                    existing_sessions.append(new_session)
            
            # Write
            output = {
                'version': '1.0',
                'exported_at': datetime.now().isoformat(),
                'sessions_count': len(existing_sessions),
                'sessions': existing_sessions
            }
            
            indent = 2 if self.pretty else None
            db_path.write_text(json.dumps(output, indent=indent, default=str), encoding='utf-8')
            self._sessions_cache = []


class JSONLOutput(BaseOutput):
    """Output sessions as JSONL (one JSON object per line)."""
    
    name = "jsonl"
    description = "JSON Lines format for streaming/processing"
    
    def __init__(self, output_dir: Path, **config):
        super().__init__(output_dir, **config)
        self.redact = config.get('redact', True)
    
    def get_session_path(self, session: Session) -> Path:
        """Get output path - always append to single file per provider."""
        return self.output_dir / f"{session.provider.value}-sessions.jsonl"
    
    def session_exists(self, session: Session) -> bool:
        """Check if session exists in JSONL file."""
        path = self.get_session_path(session)
        if not path.exists():
            return False
        
        try:
            with open(path, 'r') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        if data.get('id') == session.id:
                            return True
        except:
            pass
        
        return False
    
    def needs_update(self, session: Session) -> bool:
        """Check if needs update."""
        path = self.get_session_path(session)
        if not path.exists():
            return True
        
        try:
            with open(path, 'r') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        if data.get('id') == session.id:
                            existing_mtime = data.get('source_mtime', 0)
                            return (session.source_mtime or 0) > existing_mtime
        except:
            return True
        
        return True
    
    def write_session(self, session: Session) -> bool:
        """Append session to JSONL file."""
        if self.redact:
            for msg in session.messages:
                msg.content = redact_secrets(msg.content)
        
        path = self.get_session_path(session)
        self.ensure_dir(path.parent)
        
        session_dict = session.to_dict()
        
        # If exists, remove old entry first
        if self.session_exists(session):
            lines = []
            with open(path, 'r') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        if data.get('id') != session.id:
                            lines.append(line.strip())
            
            with open(path, 'w') as f:
                for line in lines:
                    f.write(line + '\n')
        
        # Append new
        with open(path, 'a') as f:
            f.write(json.dumps(session_dict, default=str) + '\n')
        
        return True
