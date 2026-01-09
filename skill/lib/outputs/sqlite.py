"""
SQLite output plugin.
Stores sessions in a local SQLite database for querying.
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from .base import BaseOutput
from ..models import Session, MessageRole
from ..redact import redact_secrets


class SQLiteOutput(BaseOutput):
    """Output sessions to SQLite database."""
    
    name = "sqlite"
    description = "SQLite database for fast querying"
    
    def __init__(self, output_dir: Path, **config):
        super().__init__(output_dir, **config)
        self.redact = config.get('redact', True)
        self.db_name = config.get('db_name', 'sessions.db')
        self._conn: Optional[sqlite3.Connection] = None
    
    @property
    def db_path(self) -> Path:
        return self.output_dir / self.db_name
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection, creating tables if needed."""
        if self._conn is None:
            self.ensure_dir(self.output_dir)
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._create_tables()
        return self._conn
    
    def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        conn = self._conn
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                working_dir TEXT,
                project_name TEXT,
                model TEXT,
                source_file TEXT,
                source_mtime REAL,
                summary TEXT,
                total_tokens INTEGER DEFAULT 0,
                user_messages INTEGER DEFAULT 0,
                assistant_messages INTEGER DEFAULT 0,
                tool_calls INTEGER DEFAULT 0,
                languages TEXT,
                tags TEXT,
                synced_at TEXT NOT NULL
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT,
                tool_name TEXT,
                token_estimate INTEGER DEFAULT 0,
                position INTEGER NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        ''')
        
        # Indexes for fast querying
        conn.execute('CREATE INDEX IF NOT EXISTS idx_sessions_provider ON sessions(provider)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_sessions_created ON sessions(created_at)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)')
        
        # Full-text search
        conn.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                content,
                session_id UNINDEXED,
                content=messages,
                content_rowid=id
            )
        ''')
        
        conn.commit()
    
    def session_exists(self, session: Session) -> bool:
        """Check if session exists in database."""
        conn = self._get_conn()
        cursor = conn.execute(
            'SELECT 1 FROM sessions WHERE id = ?',
            (session.id,)
        )
        return cursor.fetchone() is not None
    
    def needs_update(self, session: Session) -> bool:
        """Check if session needs update based on mtime."""
        conn = self._get_conn()
        cursor = conn.execute(
            'SELECT source_mtime FROM sessions WHERE id = ?',
            (session.id,)
        )
        row = cursor.fetchone()
        if not row:
            return True
        
        existing_mtime = row['source_mtime'] or 0
        return (session.source_mtime or 0) > existing_mtime
    
    def write_session(self, session: Session) -> bool:
        """Write session to database."""
        conn = self._get_conn()
        
        # Delete existing if updating
        if self.session_exists(session):
            conn.execute('DELETE FROM messages WHERE session_id = ?', (session.id,))
            conn.execute('DELETE FROM sessions WHERE id = ?', (session.id,))
        
        # Insert session
        conn.execute('''
            INSERT INTO sessions (
                id, provider, created_at, updated_at, working_dir, project_name,
                model, source_file, source_mtime, summary, total_tokens,
                user_messages, assistant_messages, tool_calls, languages, tags, synced_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session.id,
            session.provider.value,
            session.created_at.isoformat(),
            session.updated_at.isoformat() if session.updated_at else None,
            session.working_dir,
            session.project_name,
            session.model,
            session.source_file,
            session.source_mtime,
            session.summary,
            session.total_tokens,
            session.user_messages,
            session.assistant_messages,
            session.tool_calls,
            json.dumps(session.languages),
            json.dumps(session.tags),
            datetime.now().isoformat()
        ))
        
        # Insert messages
        for i, msg in enumerate(session.messages):
            content = redact_secrets(msg.content) if self.redact else msg.content
            
            cursor = conn.execute('''
                INSERT INTO messages (
                    session_id, role, content, timestamp, tool_name, token_estimate, position
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                session.id,
                msg.role.value,
                content,
                msg.timestamp.isoformat() if msg.timestamp else None,
                msg.tool_name,
                msg.token_estimate,
                i
            ))
            
            # Update FTS
            conn.execute('''
                INSERT INTO messages_fts (rowid, content, session_id)
                VALUES (?, ?, ?)
            ''', (cursor.lastrowid, content, session.id))
        
        conn.commit()
        return True
    
    def search(self, query: str, limit: int = 50) -> List[dict]:
        """
        Full-text search across all messages.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of matching sessions with context
        """
        conn = self._get_conn()
        
        cursor = conn.execute('''
            SELECT 
                m.session_id,
                m.content,
                m.role,
                m.position,
                s.provider,
                s.created_at,
                s.summary,
                highlight(messages_fts, 0, '<mark>', '</mark>') as highlighted
            FROM messages_fts f
            JOIN messages m ON f.rowid = m.id
            JOIN sessions s ON m.session_id = s.id
            WHERE messages_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        ''', (query, limit))
        
        results = []
        for row in cursor:
            results.append({
                'session_id': row['session_id'],
                'provider': row['provider'],
                'created_at': row['created_at'],
                'summary': row['summary'],
                'role': row['role'],
                'content': row['content'],
                'highlighted': row['highlighted'],
                'position': row['position']
            })
        
        return results
    
    def get_stats(self) -> dict:
        """Get database statistics."""
        conn = self._get_conn()
        
        stats = {}
        
        # Total sessions
        cursor = conn.execute('SELECT COUNT(*) as count FROM sessions')
        stats['total_sessions'] = cursor.fetchone()['count']
        
        # Sessions by provider
        cursor = conn.execute('''
            SELECT provider, COUNT(*) as count 
            FROM sessions 
            GROUP BY provider 
            ORDER BY count DESC
        ''')
        stats['by_provider'] = {row['provider']: row['count'] for row in cursor}
        
        # Total messages
        cursor = conn.execute('SELECT COUNT(*) as count FROM messages')
        stats['total_messages'] = cursor.fetchone()['count']
        
        # Date range
        cursor = conn.execute('''
            SELECT MIN(created_at) as first, MAX(created_at) as last 
            FROM sessions
        ''')
        row = cursor.fetchone()
        stats['date_range'] = {'first': row['first'], 'last': row['last']}
        
        return stats
    
    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
