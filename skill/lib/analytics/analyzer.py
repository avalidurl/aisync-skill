"""
Session analyzer - compute metrics and insights.
"""

import re
from typing import List, Dict, Any, Tuple
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from ..models import Session, Message, MessageRole


class SessionAnalyzer:
    """Analyze sessions and compute metrics."""
    
    # Approximate tokens per character (for estimation)
    CHARS_PER_TOKEN = 4
    
    # Code block patterns
    CODE_BLOCK_PATTERN = re.compile(r'```(\w*)\n([\s\S]*?)```', re.MULTILINE)
    INLINE_CODE_PATTERN = re.compile(r'`([^`]+)`')
    
    # Language detection patterns
    LANGUAGE_PATTERNS = {
        'python': [r'\bdef\s+\w+\s*\(', r'\bimport\s+\w+', r'\bclass\s+\w+:', r'\.py\b'],
        'javascript': [r'\bfunction\s+\w+', r'\bconst\s+\w+', r'\blet\s+\w+', r'\.js\b', r'=>'],
        'typescript': [r'\binterface\s+\w+', r':\s*\w+\[\]', r'\.ts\b', r'<\w+>'],
        'rust': [r'\bfn\s+\w+', r'\blet\s+mut\s+', r'\.rs\b', r'\bimpl\s+'],
        'go': [r'\bfunc\s+\w+', r'\bpackage\s+\w+', r'\.go\b'],
        'java': [r'\bpublic\s+class', r'\bprivate\s+\w+', r'\.java\b'],
        'c': [r'#include\s*<', r'\bint\s+main\s*\(', r'\.c\b'],
        'cpp': [r'#include\s*<', r'\bstd::', r'\.cpp\b', r'\.hpp\b'],
        'sql': [r'\bSELECT\s+', r'\bFROM\s+', r'\bWHERE\s+', r'\bINSERT\s+'],
        'bash': [r'#!/bin/bash', r'\becho\s+', r'\$\{?\w+\}?'],
        'html': [r'<html', r'<div', r'<span', r'</\w+>'],
        'css': [r'\{[^}]*:\s*[^}]+\}', r'\.[\w-]+\s*\{', r'#[\w-]+\s*\{'],
        'json': [r'^\s*\{', r'"\w+":\s*'],
        'yaml': [r'^\w+:', r'^\s+-\s+\w+'],
        'markdown': [r'^#{1,6}\s+', r'\[.*\]\(.*\)', r'^\*\s+'],
    }
    
    def analyze_session(self, session: Session) -> Session:
        """
        Analyze a session and populate analytics fields.
        
        Args:
            session: Session to analyze
            
        Returns:
            Session with populated analytics fields
        """
        # Count messages by type
        user_count = 0
        assistant_count = 0
        tool_count = 0
        total_tokens = 0
        all_code_blocks = []
        all_languages = set()
        
        for msg in session.messages:
            # Count by role
            if msg.role == MessageRole.USER:
                user_count += 1
            elif msg.role == MessageRole.ASSISTANT:
                assistant_count += 1
            elif msg.role == MessageRole.TOOL:
                tool_count += 1
            
            # Estimate tokens
            msg.token_estimate = len(msg.content) // self.CHARS_PER_TOKEN
            total_tokens += msg.token_estimate
            
            # Extract code blocks
            code_blocks = self._extract_code_blocks(msg.content)
            msg.code_blocks = [cb[1] for cb in code_blocks]
            msg.languages_detected = list(set(cb[0] for cb in code_blocks if cb[0]))
            
            all_code_blocks.extend(code_blocks)
            all_languages.update(msg.languages_detected)
            
            # Detect languages in content
            detected = self._detect_languages(msg.content)
            all_languages.update(detected)
        
        # Update session
        session.user_messages = user_count
        session.assistant_messages = assistant_count
        session.tool_calls = tool_count
        session.total_tokens = total_tokens
        session.code_blocks_count = len(all_code_blocks)
        session.languages = list(all_languages)
        
        # Estimate duration (rough: ~30s per exchange)
        exchanges = min(user_count, assistant_count)
        session.duration_estimate = exchanges * 30
        
        return session
    
    def _extract_code_blocks(self, content: str) -> List[Tuple[str, str]]:
        """Extract code blocks with language hints."""
        blocks = []
        
        for match in self.CODE_BLOCK_PATTERN.finditer(content):
            lang = match.group(1).lower() or None
            code = match.group(2)
            
            # Try to detect language if not specified
            if not lang:
                detected = self._detect_languages(code)
                lang = detected[0] if detected else None
            
            blocks.append((lang, code))
        
        return blocks
    
    def _detect_languages(self, content: str) -> List[str]:
        """Detect programming languages in content."""
        detected = []
        
        for lang, patterns in self.LANGUAGE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                    detected.append(lang)
                    break
        
        return detected
    
    def analyze_sessions(self, sessions: List[Session]) -> List[Session]:
        """Analyze multiple sessions."""
        return [self.analyze_session(s) for s in sessions]
    
    def get_aggregate_stats(self, sessions: List[Session]) -> Dict[str, Any]:
        """
        Get aggregate statistics across all sessions.
        
        Args:
            sessions: List of analyzed sessions
            
        Returns:
            Dictionary of statistics
        """
        if not sessions:
            return {}
        
        # Basic counts
        total_sessions = len(sessions)
        total_messages = sum(s.user_messages + s.assistant_messages for s in sessions)
        total_tokens = sum(s.total_tokens for s in sessions)
        total_code_blocks = sum(s.code_blocks_count for s in sessions)
        
        # By provider
        by_provider = Counter(s.provider.value for s in sessions)
        
        # By language
        all_langs = []
        for s in sessions:
            all_langs.extend(s.languages)
        by_language = Counter(all_langs)
        
        # By date
        by_date = Counter(s.date_str for s in sessions)
        
        # Time range
        dates = [s.created_at for s in sessions]
        date_range = (min(dates), max(dates)) if dates else (None, None)
        
        # Activity by hour
        by_hour = Counter(s.created_at.hour for s in sessions)
        
        # Activity by day of week
        by_day = Counter(s.created_at.strftime('%A') for s in sessions)
        
        # Models used
        models = [s.model for s in sessions if s.model]
        by_model = Counter(models)
        
        # Average messages per session
        avg_messages = total_messages / total_sessions if total_sessions else 0
        avg_tokens = total_tokens / total_sessions if total_sessions else 0
        
        return {
            'total_sessions': total_sessions,
            'total_messages': total_messages,
            'total_tokens': total_tokens,
            'total_code_blocks': total_code_blocks,
            'avg_messages_per_session': round(avg_messages, 1),
            'avg_tokens_per_session': round(avg_tokens, 0),
            'by_provider': dict(by_provider.most_common()),
            'by_language': dict(by_language.most_common(10)),
            'by_date': dict(by_date.most_common(30)),
            'by_hour': dict(sorted(by_hour.items())),
            'by_day_of_week': dict(by_day.most_common()),
            'by_model': dict(by_model.most_common()),
            'date_range': {
                'start': date_range[0].isoformat() if date_range[0] else None,
                'end': date_range[1].isoformat() if date_range[1] else None
            }
        }
