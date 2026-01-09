"""
Base output plugin class.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Dict, Any

from ..models import Session, SyncResult


class BaseOutput(ABC):
    """Abstract base class for output plugins."""
    
    name: str = "base"
    description: str = "Base output plugin"
    
    def __init__(self, output_dir: Path, **config):
        """
        Initialize output plugin.
        
        Args:
            output_dir: Base output directory
            **config: Plugin-specific configuration
        """
        self.output_dir = Path(output_dir)
        self.config = config
    
    @abstractmethod
    def write_session(self, session: Session) -> bool:
        """
        Write a single session.
        
        Args:
            session: Session to write
            
        Returns:
            True if written, False if skipped (already exists)
        """
        pass
    
    @abstractmethod
    def session_exists(self, session: Session) -> bool:
        """
        Check if session already exists in output.
        
        Args:
            session: Session to check
            
        Returns:
            True if exists
        """
        pass
    
    @abstractmethod
    def needs_update(self, session: Session) -> bool:
        """
        Check if session needs to be updated.
        
        Args:
            session: Session to check
            
        Returns:
            True if session needs update
        """
        pass
    
    def write_sessions(self, sessions: List[Session]) -> SyncResult:
        """
        Write multiple sessions.
        
        Args:
            sessions: List of sessions to write
            
        Returns:
            SyncResult with statistics
        """
        import time
        start = time.time()
        
        result = SyncResult(
            provider=sessions[0].provider if sessions else None,
            sessions_found=len(sessions)
        )
        
        for session in sessions:
            try:
                if not self.session_exists(session):
                    if self.write_session(session):
                        result.sessions_synced += 1
                    else:
                        result.sessions_failed += 1
                elif self.needs_update(session):
                    if self.write_session(session):
                        result.sessions_synced += 1
                    else:
                        result.sessions_failed += 1
                else:
                    result.sessions_skipped += 1
            except Exception as e:
                result.sessions_failed += 1
                result.errors.append(f"{session.id}: {str(e)}")
        
        result.duration_ms = (time.time() - start) * 1000
        return result
    
    def ensure_dir(self, path: Path) -> None:
        """Ensure directory exists."""
        path.mkdir(parents=True, exist_ok=True)
    
    def get_session_filename(self, session: Session) -> str:
        """Generate filename for session."""
        return f"{session.provider.value}-{session.date_str}-{session.time_str.replace(':', '')}-{session.id}"
