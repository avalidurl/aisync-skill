"""
HTML output plugin.
Generates a static website for browsing sessions.
"""

from pathlib import Path
from typing import List
from datetime import datetime
import html

from .base import BaseOutput
from ..models import Session, MessageRole
from ..redact import redact_secrets


class HTMLOutput(BaseOutput):
    """Output sessions as a static HTML website."""
    
    name = "html"
    description = "Static HTML website for browsing sessions"
    
    def __init__(self, output_dir: Path, **config):
        super().__init__(output_dir, **config)
        self.redact = config.get('redact', True)
        self.theme = config.get('theme', 'dark')  # dark or light
        self._sessions: List[Session] = []
    
    def get_session_path(self, session: Session) -> Path:
        """Get output path for session."""
        folder = f"{session.provider.value}"
        filename = f"{self.get_session_filename(session)}.html"
        return self.output_dir / "sessions" / folder / filename
    
    def session_exists(self, session: Session) -> bool:
        """Check if session HTML exists."""
        return self.get_session_path(session).exists()
    
    def needs_update(self, session: Session) -> bool:
        """Check if session needs update."""
        path = self.get_session_path(session)
        if not path.exists():
            return True
        
        if session.source_mtime:
            return session.source_mtime > path.stat().st_mtime
        
        return False
    
    def write_session(self, session: Session) -> bool:
        """Write session as HTML page."""
        self._sessions.append(session)
        
        path = self.get_session_path(session)
        self.ensure_dir(path.parent)
        
        html_content = self._generate_session_html(session)
        path.write_text(html_content, encoding='utf-8')
        return True
    
    def finalize(self) -> None:
        """Generate index and assets."""
        self._write_index()
        self._write_css()
        self._write_search_js()
    
    def _generate_session_html(self, session: Session) -> str:
        """Generate HTML for a session."""
        provider_name = session.provider.value.replace('-', ' ').title()
        
        messages_html = ""
        for msg in session.messages:
            content = redact_secrets(msg.content) if self.redact else msg.content
            content_escaped = html.escape(content).replace('\n', '<br>')
            
            if msg.role == MessageRole.USER:
                messages_html += f'''
                <div class="message user">
                    <div class="message-header">👤 User</div>
                    <div class="message-content">{content_escaped}</div>
                </div>
                '''
            else:
                messages_html += f'''
                <div class="message assistant">
                    <div class="message-header">🤖 {provider_name}</div>
                    <div class="message-content">{content_escaped}</div>
                </div>
                '''
        
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{provider_name} Session - {session.date_str}</title>
    <link rel="stylesheet" href="../../assets/style.css">
</head>
<body class="{self.theme}">
    <nav>
        <a href="../../index.html">← Back to Index</a>
    </nav>
    
    <header>
        <h1>{provider_name} Session</h1>
        <div class="metadata">
            <span class="date">📅 {session.date_str} {session.time_str}</span>
            <span class="id">🔑 {session.id}</span>
            {f'<span class="model">🧠 {session.model}</span>' if session.model else ''}
            {f'<span class="dir">📁 {session.working_dir}</span>' if session.working_dir else ''}
        </div>
    </header>
    
    <main>
        {messages_html}
    </main>
    
    <footer>
        <p>Synced at {datetime.now().isoformat()} • Secrets redacted</p>
    </footer>
</body>
</html>'''
    
    def _write_index(self) -> None:
        """Write index.html with session list."""
        self.ensure_dir(self.output_dir)
        
        # Group sessions by provider
        by_provider = {}
        for session in self._sessions:
            provider = session.provider.value
            if provider not in by_provider:
                by_provider[provider] = []
            by_provider[provider].append(session)
        
        # Sort each group by date
        for sessions in by_provider.values():
            sessions.sort(key=lambda s: s.created_at, reverse=True)
        
        # Generate provider sections
        sections_html = ""
        for provider, sessions in sorted(by_provider.items()):
            provider_name = provider.replace('-', ' ').title()
            
            sessions_html = ""
            for session in sessions[:50]:  # Limit to 50 per provider
                path = f"sessions/{provider}/{self.get_session_filename(session)}.html"
                summary = html.escape(session.summary[:60])
                sessions_html += f'''
                <li>
                    <a href="{path}">
                        <span class="date">{session.date_str}</span>
                        <span class="summary">{summary}</span>
                    </a>
                </li>
                '''
            
            sections_html += f'''
            <section class="provider-section">
                <h2>{provider_name} <span class="count">({len(sessions)})</span></h2>
                <ul class="session-list">
                    {sessions_html}
                </ul>
            </section>
            '''
        
        index_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Sessions Archive</title>
    <link rel="stylesheet" href="assets/style.css">
</head>
<body class="{self.theme}">
    <header>
        <h1>🤖 AI Sessions Archive</h1>
        <p>{len(self._sessions)} sessions from {len(by_provider)} providers</p>
        <input type="search" id="search" placeholder="Search sessions...">
    </header>
    
    <main>
        {sections_html}
    </main>
    
    <footer>
        <p>Generated by AI Sessions Sync • {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    </footer>
    
    <script src="assets/search.js"></script>
</body>
</html>'''
        
        (self.output_dir / "index.html").write_text(index_html, encoding='utf-8')
    
    def _write_css(self) -> None:
        """Write CSS stylesheet."""
        self.ensure_dir(self.output_dir / "assets")
        
        css = '''
:root {
    --bg-primary: #1a1a2e;
    --bg-secondary: #16213e;
    --text-primary: #eee;
    --text-secondary: #aaa;
    --accent: #e94560;
    --user-bg: #0f3460;
    --assistant-bg: #1a1a2e;
    --border: #333;
}

body.light {
    --bg-primary: #f5f5f5;
    --bg-secondary: #fff;
    --text-primary: #333;
    --text-secondary: #666;
    --accent: #e94560;
    --user-bg: #e3f2fd;
    --assistant-bg: #fff;
    --border: #ddd;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    line-height: 1.6;
}

nav {
    padding: 1rem 2rem;
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border);
}

nav a {
    color: var(--accent);
    text-decoration: none;
}

header {
    padding: 2rem;
    text-align: center;
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border);
}

header h1 { margin-bottom: 0.5rem; }
header p { color: var(--text-secondary); }

header input[type="search"] {
    margin-top: 1rem;
    padding: 0.75rem 1rem;
    width: 100%;
    max-width: 400px;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--bg-primary);
    color: var(--text-primary);
    font-size: 1rem;
}

main { padding: 2rem; max-width: 1200px; margin: 0 auto; }

.metadata {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    justify-content: center;
    margin-top: 1rem;
    color: var(--text-secondary);
}

.provider-section {
    margin-bottom: 2rem;
}

.provider-section h2 {
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid var(--accent);
}

.provider-section .count {
    font-weight: normal;
    color: var(--text-secondary);
}

.session-list {
    list-style: none;
}

.session-list li {
    margin-bottom: 0.5rem;
}

.session-list a {
    display: flex;
    gap: 1rem;
    padding: 0.75rem 1rem;
    background: var(--bg-secondary);
    border-radius: 8px;
    text-decoration: none;
    color: var(--text-primary);
    transition: transform 0.2s;
}

.session-list a:hover {
    transform: translateX(5px);
}

.session-list .date {
    color: var(--accent);
    font-family: monospace;
}

.message {
    margin-bottom: 1.5rem;
    padding: 1rem;
    border-radius: 8px;
}

.message.user { background: var(--user-bg); }
.message.assistant { background: var(--assistant-bg); border: 1px solid var(--border); }

.message-header {
    font-weight: bold;
    margin-bottom: 0.5rem;
    color: var(--accent);
}

.message-content {
    white-space: pre-wrap;
    word-wrap: break-word;
}

footer {
    padding: 2rem;
    text-align: center;
    color: var(--text-secondary);
    border-top: 1px solid var(--border);
}
'''
        
        (self.output_dir / "assets" / "style.css").write_text(css, encoding='utf-8')
    
    def _write_search_js(self) -> None:
        """Write search JavaScript."""
        js = '''
document.addEventListener('DOMContentLoaded', function() {
    const search = document.getElementById('search');
    if (!search) return;
    
    search.addEventListener('input', function(e) {
        const query = e.target.value.toLowerCase();
        const items = document.querySelectorAll('.session-list li');
        
        items.forEach(item => {
            const text = item.textContent.toLowerCase();
            item.style.display = text.includes(query) ? '' : 'none';
        });
    });
});
'''
        (self.output_dir / "assets" / "search.js").write_text(js, encoding='utf-8')
