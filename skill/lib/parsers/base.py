"""
Base parser class for AI session files.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Generator
import os
import platform

from ..models import Session, Provider


class BaseParser(ABC):
    """Abstract base class for session parsers."""
    
    provider: Provider
    
    def __init__(self, home_dir: Optional[str] = None):
        """
        Initialize parser.
        
        Args:
            home_dir: Home directory path (defaults to os.path.expanduser('~'))
        """
        self.home_dir = Path(home_dir) if home_dir else Path.home()
        self.system = platform.system()
    
    @abstractmethod
    def get_session_paths(self) -> List[Path]:
        """
        Get all session file/directory paths for this provider.
        
        Returns:
            List of paths to session files or directories
        """
        pass
    
    @abstractmethod
    def parse_session(self, path: Path) -> Optional[Session]:
        """
        Parse a single session from a file or directory.
        
        Args:
            path: Path to session file or directory
            
        Returns:
            Parsed Session or None if parsing fails
        """
        pass
    
    def parse_all(self) -> Generator[Session, None, None]:
        """
        Parse all sessions for this provider.
        
        Yields:
            Parsed sessions
        """
        paths = self.get_session_paths()
        for path in paths:
            try:
                session = self.parse_session(path)
                if session:
                    yield session
            except Exception as e:
                # Log error but continue
                print(f"Error parsing {path}: {e}")
                continue
    
    def get_vscode_global_storage(self) -> Path:
        """Get VS Code global storage path for current platform."""
        if self.system == "Darwin":
            return self.home_dir / "Library/Application Support/Code/User/globalStorage"
        elif self.system == "Linux":
            return self.home_dir / ".config/Code/User/globalStorage"
        elif self.system == "Windows":
            appdata = Path(os.environ.get('APPDATA', self.home_dir / 'AppData/Roaming'))
            return appdata / "Code/User/globalStorage"
        else:
            return self.home_dir / ".config/Code/User/globalStorage"
    
    def get_cursor_global_storage(self) -> Path:
        """Get Cursor global storage path for current platform."""
        if self.system == "Darwin":
            return self.home_dir / "Library/Application Support/Cursor/User/globalStorage"
        elif self.system == "Linux":
            return self.home_dir / ".config/Cursor/User/globalStorage"
        elif self.system == "Windows":
            appdata = Path(os.environ.get('APPDATA', self.home_dir / 'AppData/Roaming'))
            return appdata / "Cursor/User/globalStorage"
        else:
            return self.home_dir / ".config/Cursor/User/globalStorage"
    
    def find_files(self, base_dir: Path, pattern: str, max_depth: int = 10) -> List[Path]:
        """
        Find files matching pattern in directory.
        
        Args:
            base_dir: Base directory to search
            pattern: Glob pattern (e.g., "*.jsonl")
            max_depth: Maximum directory depth
            
        Returns:
            List of matching file paths
        """
        if not base_dir.exists():
            return []
        
        results = []
        try:
            for path in base_dir.rglob(pattern):
                # Check depth
                relative = path.relative_to(base_dir)
                if len(relative.parts) <= max_depth:
                    results.append(path)
        except PermissionError:
            pass
        
        return results
