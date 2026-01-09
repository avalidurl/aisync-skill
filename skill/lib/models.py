"""
Core data models for AI Sessions Sync.
These models are output-agnostic and can be serialized to any format.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
import json


class Provider(Enum):
    """Supported AI coding tools."""
    CLAUDE_CODE = "claude-code"
    CODEX = "codex"
    CURSOR = "cursor"
    AIDER = "aider"
    CLINE = "cline"
    GEMINI_CLI = "gemini-cli"
    CONTINUE = "continue"
    COPILOT = "copilot"
    ROO_CODE = "roo-code"
    WINDSURF = "windsurf"
    ZED_AI = "zed-ai"
    AMP = "amp"
    OPENCODE = "opencode"
    OPENROUTER = "openrouter"


class MessageRole(Enum):
    """Message roles in a conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class Message:
    """A single message in a conversation."""
    role: MessageRole
    content: str
    timestamp: Optional[datetime] = None
    tool_name: Optional[str] = None  # For tool calls
    tool_input: Optional[Dict[str, Any]] = None
    tool_result: Optional[str] = None
    
    # Analytics fields (computed)
    token_estimate: int = 0
    code_blocks: List[str] = field(default_factory=list)
    languages_detected: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        d = {
            'role': self.role.value,
            'content': self.content,
        }
        if self.timestamp:
            d['timestamp'] = self.timestamp.isoformat()
        if self.tool_name:
            d['tool_name'] = self.tool_name
        if self.tool_input:
            d['tool_input'] = self.tool_input
        if self.tool_result:
            d['tool_result'] = self.tool_result
        if self.token_estimate:
            d['token_estimate'] = self.token_estimate
        if self.code_blocks:
            d['code_blocks'] = self.code_blocks
        if self.languages_detected:
            d['languages_detected'] = self.languages_detected
        return d


@dataclass
class Session:
    """A complete AI coding session."""
    id: str
    provider: Provider
    messages: List[Message]
    
    # Metadata
    created_at: datetime
    updated_at: Optional[datetime] = None
    working_dir: Optional[str] = None
    project_name: Optional[str] = None
    model: Optional[str] = None
    
    # Source info
    source_file: Optional[str] = None
    source_mtime: Optional[float] = None
    
    # Analytics (computed)
    total_tokens: int = 0
    user_messages: int = 0
    assistant_messages: int = 0
    tool_calls: int = 0
    code_blocks_count: int = 0
    languages: List[str] = field(default_factory=list)
    duration_estimate: Optional[float] = None  # seconds
    
    # Tags (for categorization)
    tags: List[str] = field(default_factory=list)
    
    @property
    def summary(self) -> str:
        """Get first user message as summary."""
        for msg in self.messages:
            if msg.role == MessageRole.USER:
                return msg.content[:100].replace('\n', ' ').strip() + "..."
        return "Session"
    
    @property
    def date_str(self) -> str:
        """Get date as string."""
        return self.created_at.strftime('%Y-%m-%d')
    
    @property
    def time_str(self) -> str:
        """Get time as string."""
        return self.created_at.strftime('%H:%M')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'provider': self.provider.value,
            'messages': [m.to_dict() for m in self.messages],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'working_dir': self.working_dir,
            'project_name': self.project_name,
            'model': self.model,
            'source_file': self.source_file,
            'total_tokens': self.total_tokens,
            'user_messages': self.user_messages,
            'assistant_messages': self.assistant_messages,
            'tool_calls': self.tool_calls,
            'code_blocks_count': self.code_blocks_count,
            'languages': self.languages,
            'duration_estimate': self.duration_estimate,
            'tags': self.tags,
            'summary': self.summary,
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)


@dataclass
class SyncResult:
    """Result of a sync operation."""
    provider: Provider
    sessions_found: int = 0
    sessions_synced: int = 0
    sessions_skipped: int = 0
    sessions_failed: int = 0
    errors: List[str] = field(default_factory=list)
    duration_ms: float = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SearchResult:
    """A search result."""
    session: Session
    message: Message
    score: float
    context_before: List[Message] = field(default_factory=list)
    context_after: List[Message] = field(default_factory=list)
    highlights: List[str] = field(default_factory=list)
