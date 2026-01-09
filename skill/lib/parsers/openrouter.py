"""
Parser for OpenRouter sessions.

OpenRouter stores conversations locally in browser localStorage when using their
chatroom interface. Users can export conversations from the settings menu.

This parser supports:
1. Exported conversations (JSON files in ~/Downloads or configured export directory)
2. openrouter-kit SDK exports (if using DiskHistoryStorage)
3. Custom export directories

Storage locations checked:
- ~/Downloads/openrouter*.json
- ~/openrouter-exports/
- ~/.config/openrouter/exports/
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
import re

from .base import BaseParser
from ..models import Session, Message, Provider, MessageRole


class OpenRouterParser(BaseParser):
    """Parser for OpenRouter exported sessions."""
    
    provider = Provider.OPENROUTER
    
    def get_session_paths(self) -> List[Path]:
        """Get all OpenRouter export files."""
        paths = []
        
        # Check common export locations
        export_dirs = [
            self.home_dir / "Downloads",
            self.home_dir / "openrouter-exports",
            self.home_dir / ".config" / "openrouter" / "exports",
            self.home_dir / ".openrouter",
        ]
        
        # Also check for openrouter-kit DiskHistoryStorage default location
        openrouter_kit_dir = self.home_dir / ".openrouter-kit" / "history"
        if openrouter_kit_dir.exists():
            export_dirs.append(openrouter_kit_dir)
        
        for export_dir in export_dirs:
            if not export_dir.exists():
                continue
            
            # Look for OpenRouter export files
            for pattern in ["openrouter*.json", "openrouter*.jsonl", 
                           "chat*.json", "conversation*.json",
                           "*.openrouter.json"]:
                paths.extend(export_dir.glob(pattern))
            
            # Also check subdirectories one level deep
            for subdir in export_dir.iterdir():
                if subdir.is_dir() and "openrouter" in subdir.name.lower():
                    paths.extend(self.find_files(subdir, "*.json"))
                    paths.extend(self.find_files(subdir, "*.jsonl"))
        
        # Deduplicate
        return list(set(paths))
    
    def parse_session(self, path: Path) -> Optional[Session]:
        """Parse an OpenRouter export file."""
        try:
            content = path.read_text(encoding='utf-8')
        except Exception:
            return None
        
        messages: List[Message] = []
        model = ""
        created_at = None
        session_id = ""
        
        # Handle JSONL format
        if path.suffix == '.jsonl':
            for line in content.split('\n'):
                if line.strip():
                    try:
                        entry = json.loads(line)
                        self._extract_message(entry, messages)
                        if entry.get('model') and not model:
                            model = entry['model']
                        if entry.get('timestamp') and not created_at:
                            created_at = self._parse_timestamp(entry['timestamp'])
                    except json.JSONDecodeError:
                        pass
        else:
            # Handle JSON
            try:
                data = json.loads(content)
                
                # Handle array of conversations (export format)
                if isinstance(data, list):
                    for entry in data:
                        if isinstance(entry, dict):
                            # Check if this is a conversation object
                            if 'messages' in entry:
                                for msg in entry['messages']:
                                    self._extract_message(msg, messages)
                                if entry.get('model'):
                                    model = entry['model']
                                if entry.get('id'):
                                    session_id = str(entry['id'])[:8]
                            else:
                                self._extract_message(entry, messages)
                                if entry.get('model') and not model:
                                    model = entry['model']
                
                # Handle single conversation object
                elif isinstance(data, dict):
                    session_id = str(data.get('id', ''))[:8] if data.get('id') else ''
                    model = data.get('model', '')
                    
                    # Try various message array keys
                    conversation = (
                        data.get('messages', []) or
                        data.get('conversation', []) or
                        data.get('history', []) or
                        data.get('chat', [])
                    )
                    
                    for msg in conversation:
                        self._extract_message(msg, messages)
                    
                    # Extract timestamp
                    if data.get('created_at'):
                        created_at = self._parse_timestamp(data['created_at'])
                    elif data.get('createdAt'):
                        created_at = self._parse_timestamp(data['createdAt'])
                    elif data.get('timestamp'):
                        created_at = self._parse_timestamp(data['timestamp'])
                    
            except json.JSONDecodeError:
                return None
        
        if not messages:
            return None
        
        if not session_id:
            session_id = path.stem[:8]
        
        if not created_at:
            created_at = self.get_file_created_at(path)
        
        # Extract model from filename if not in data
        if not model:
            model = self._extract_model_from_filename(path.name)
        
        return Session(
            id=session_id,
            provider=self.provider,
            messages=messages,
            created_at=created_at,
            model=model,
            source_file=str(path),
            source_mtime=path.stat().st_mtime,
            tags=['openrouter', 'ai-session', 'multi-model']
        )
    
    def _extract_message(self, entry: dict, messages: List[Message]) -> None:
        """Extract message from entry."""
        if not isinstance(entry, dict):
            return
        
        role = entry.get('role', '').lower()
        content = entry.get('content', entry.get('text', ''))
        
        # Handle content that might be a list (OpenAI format)
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    if item.get('type') == 'text' and item.get('text'):
                        parts.append(item['text'])
                    elif item.get('type') == 'image_url':
                        parts.append("[Image]")
            content = '\n\n'.join(parts)
        
        if not content:
            return
        
        timestamp = None
        for ts_key in ['timestamp', 'created_at', 'createdAt']:
            if entry.get(ts_key):
                timestamp = self._parse_timestamp(entry[ts_key])
                if timestamp:
                    break
        
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
        elif role in ('tool', 'function'):
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
    
    def _extract_model_from_filename(self, filename: str) -> str:
        """Try to extract model name from filename."""
        # Common patterns: openrouter-claude-3-opus-2024-01-01.json
        filename = filename.lower()
        
        model_patterns = [
            r'claude[_-]?3[_-]?(opus|sonnet|haiku)',
            r'gpt[_-]?4[_-]?(turbo|o)?',
            r'gemini[_-]?(pro|ultra|flash)',
            r'llama[_-]?3',
            r'mistral[_-]?(large|medium|small)?',
            r'perplexity',
        ]
        
        for pattern in model_patterns:
            match = re.search(pattern, filename)
            if match:
                return match.group(0).replace('_', '-')
        
        return ""
