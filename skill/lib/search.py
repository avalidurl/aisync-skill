"""
Search functionality for AI sessions.
"""

import re
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from .models import Session, Message, MessageRole, SearchResult


@dataclass
class SearchOptions:
    """Search options."""
    query: str
    provider: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    role: Optional[MessageRole] = None
    case_sensitive: bool = False
    regex: bool = False
    limit: int = 50
    context_lines: int = 2


class SessionSearch:
    """Search across sessions."""
    
    def __init__(self, sessions: List[Session]):
        """
        Initialize search with sessions.
        
        Args:
            sessions: List of sessions to search
        """
        self.sessions = sessions
        self._index: Dict[str, List[tuple]] = {}  # word -> [(session_idx, msg_idx)]
        self._build_index()
    
    def _build_index(self) -> None:
        """Build search index."""
        for s_idx, session in enumerate(self.sessions):
            for m_idx, msg in enumerate(session.messages):
                # Tokenize content
                words = re.findall(r'\b\w+\b', msg.content.lower())
                for word in set(words):  # unique words only
                    if word not in self._index:
                        self._index[word] = []
                    self._index[word].append((s_idx, m_idx))
    
    def search(self, options: SearchOptions) -> List[SearchResult]:
        """
        Search sessions.
        
        Args:
            options: Search options
            
        Returns:
            List of search results
        """
        results = []
        
        # Prepare query
        if options.regex:
            try:
                flags = 0 if options.case_sensitive else re.IGNORECASE
                pattern = re.compile(options.query, flags)
            except re.error:
                return []
        else:
            query = options.query if options.case_sensitive else options.query.lower()
        
        # Search through sessions
        for session in self.sessions:
            # Filter by provider
            if options.provider and session.provider.value != options.provider:
                continue
            
            # Filter by date
            if options.date_from and session.created_at < options.date_from:
                continue
            if options.date_to and session.created_at > options.date_to:
                continue
            
            # Search messages
            for m_idx, msg in enumerate(session.messages):
                # Filter by role
                if options.role and msg.role != options.role:
                    continue
                
                # Check for match
                content = msg.content if options.case_sensitive else msg.content.lower()
                
                if options.regex:
                    match = pattern.search(msg.content)
                    if not match:
                        continue
                    score = 1.0
                    highlights = [match.group()]
                else:
                    if query not in content:
                        continue
                    # Simple scoring based on frequency
                    score = content.count(query) / len(content) * 100
                    highlights = [query]
                
                # Get context
                context_before = session.messages[max(0, m_idx - options.context_lines):m_idx]
                context_after = session.messages[m_idx + 1:m_idx + 1 + options.context_lines]
                
                results.append(SearchResult(
                    session=session,
                    message=msg,
                    score=score,
                    context_before=context_before,
                    context_after=context_after,
                    highlights=highlights
                ))
                
                if len(results) >= options.limit:
                    break
            
            if len(results) >= options.limit:
                break
        
        # Sort by score
        results.sort(key=lambda r: r.score, reverse=True)
        
        return results[:options.limit]
    
    def search_simple(self, query: str, limit: int = 50) -> List[SearchResult]:
        """Simple search with default options."""
        return self.search(SearchOptions(query=query, limit=limit))
    
    def find_similar(self, session: Session, limit: int = 5) -> List[Session]:
        """
        Find sessions similar to given session.
        
        Args:
            session: Reference session
            limit: Maximum results
            
        Returns:
            List of similar sessions
        """
        # Extract keywords from session
        all_content = ' '.join(m.content for m in session.messages)
        words = re.findall(r'\b\w{4,}\b', all_content.lower())  # 4+ char words
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Get top keywords
        keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:20]
        
        # Score other sessions
        scores = {}
        for other in self.sessions:
            if other.id == session.id:
                continue
            
            other_content = ' '.join(m.content for m in other.messages).lower()
            score = sum(
                freq * other_content.count(word)
                for word, freq in keywords
            )
            
            if score > 0:
                scores[other.id] = (other, score)
        
        # Return top matches
        sorted_sessions = sorted(scores.values(), key=lambda x: x[1], reverse=True)
        return [s for s, _ in sorted_sessions[:limit]]


def highlight_matches(text: str, query: str, tag: str = 'mark') -> str:
    """
    Highlight matches in text with HTML tags.
    
    Args:
        text: Text to highlight
        query: Query to highlight
        tag: HTML tag to use
        
    Returns:
        Text with highlights
    """
    if not query:
        return text
    
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    return pattern.sub(f'<{tag}>\\g<0></{tag}>', text)
