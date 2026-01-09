"""
AI Sessions Sync Library
========================

A modular library for syncing AI coding sessions to various outputs.

Features:
- Parse sessions from 12 AI coding tools
- Multiple output formats (Obsidian, JSON, HTML, SQLite)
- Analytics and insights
- Search functionality
- Secret redaction

Quick Start:
    from aisync import sync_all
    
    # Sync to Obsidian (default)
    results = sync_all(output_dir="~/Documents/Obsidian/ai-sessions")
    
    # Sync to multiple outputs
    results = sync_all(
        output_dir="~/ai-sessions",
        outputs=['obsidian', 'sqlite', 'json']
    )

"""

__version__ = '2.0.0'
__author__ = 'Gökhan Turhan'

from .models import Session, Message, Provider, MessageRole, SyncResult
from .redact import redact_secrets, SecretRedactor
from .parsers import get_parser, get_all_parsers, PARSERS
from .outputs import get_output, list_outputs, OUTPUTS
from .analytics import SessionAnalyzer, generate_insights
from .search import SessionSearch, SearchOptions

from pathlib import Path
from typing import List, Dict, Optional, Any
import os


def get_default_vault() -> Optional[Path]:
    """Auto-detect Obsidian vault location."""
    import platform
    
    home = Path.home()
    system = platform.system()
    
    # Check environment variable
    env_vault = os.environ.get('OBSIDIAN_VAULT')
    if env_vault:
        path = Path(env_vault)
        if path.exists():
            return path
    
    # Check config file
    config = home / ".aisync.conf"
    if config.exists():
        try:
            for line in config.read_text().split('\n'):
                if line.startswith('OBSIDIAN_VAULT='):
                    vault = line.split('=', 1)[1].strip().strip('"\'')
                    path = Path(vault).expanduser()
                    if path.exists():
                        return path
        except:
            pass
    
    # Platform-specific defaults
    if system == "Darwin":
        candidates = [
            home / "Library/Mobile Documents/iCloud~md~obsidian/Documents",
            home / "Documents/Obsidian",
        ]
    elif system == "Linux":
        candidates = [
            home / "Documents/Obsidian",
            home / "Obsidian",
        ]
    else:
        candidates = [
            home / "Documents/Obsidian",
            home / "Obsidian",
        ]
    
    for base in candidates:
        if base.exists():
            # Look for vault (has .obsidian folder)
            for item in base.iterdir():
                if item.is_dir() and (item / ".obsidian").exists():
                    return item
            # Or use base if it's a vault itself
            if (base / ".obsidian").exists():
                return base
    
    return None


def sync_all(
    output_dir: Optional[str] = None,
    outputs: List[str] = ['obsidian'],
    providers: Optional[List[str]] = None,
    analyze: bool = True,
    home_dir: Optional[str] = None,
    **config
) -> Dict[str, Any]:
    """
    Sync all AI sessions.
    
    Args:
        output_dir: Output directory (auto-detects Obsidian vault if None)
        outputs: List of output formats ('obsidian', 'json', 'html', 'sqlite')
        providers: List of providers to sync (None = all)
        analyze: Run analytics on sessions
        home_dir: Home directory override
        **config: Additional config passed to output plugins
        
    Returns:
        Dictionary with sync results and statistics
    """
    # Determine output directory
    if output_dir is None:
        vault = get_default_vault()
        if vault:
            output_dir = vault / "ai-sessions"
        else:
            output_dir = Path.home() / "ai-sessions"
    else:
        output_dir = Path(output_dir).expanduser()
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get parsers
    all_parsers = get_all_parsers(home_dir)
    if providers:
        all_parsers = {p: parser for p, parser in all_parsers.items() 
                       if p.value in providers}
    
    # Parse all sessions
    all_sessions: List[Session] = []
    parse_results = {}
    
    for provider, parser in all_parsers.items():
        sessions = list(parser.parse_all())
        all_sessions.extend(sessions)
        parse_results[provider.value] = len(sessions)
    
    # Analyze if requested
    if analyze:
        analyzer = SessionAnalyzer()
        all_sessions = analyzer.analyze_sessions(all_sessions)
        stats = analyzer.get_aggregate_stats(all_sessions)
    else:
        stats = {}
    
    # Write to outputs
    sync_results = {}
    for output_name in outputs:
        output = get_output(output_name, output_dir, **config)
        result = output.write_sessions(all_sessions)
        sync_results[output_name] = result.to_dict()
        
        # Finalize if method exists
        if hasattr(output, 'finalize'):
            output.finalize()
        if hasattr(output, 'close'):
            output.close()
    
    return {
        'output_dir': str(output_dir),
        'sessions_total': len(all_sessions),
        'by_provider': parse_results,
        'sync_results': sync_results,
        'statistics': stats if analyze else None
    }


__all__ = [
    # Version
    '__version__',
    
    # Models
    'Session',
    'Message', 
    'Provider',
    'MessageRole',
    'SyncResult',
    
    # Redaction
    'redact_secrets',
    'SecretRedactor',
    
    # Parsers
    'get_parser',
    'get_all_parsers',
    'PARSERS',
    
    # Outputs
    'get_output',
    'list_outputs',
    'OUTPUTS',
    
    # Analytics
    'SessionAnalyzer',
    'generate_insights',
    
    # Search
    'SessionSearch',
    'SearchOptions',
    
    # Convenience
    'get_default_vault',
    'sync_all',
]
