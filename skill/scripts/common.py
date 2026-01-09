#!/usr/bin/env python3
"""
Common utilities for AI session sync scripts.
Shared secret patterns, redaction, and formatting functions.
"""

import re
from pathlib import Path

# Default Obsidian vault path (can be overridden)
DEFAULT_OBSIDIAN_VAULT = Path.home() / "Library/Mobile Documents/iCloud~md~obsidian/Documents/zettelkasten"

# Comprehensive secret patterns to redact (merged from all scripts)
SECRET_PATTERNS = [
    # OpenAI
    (r'sk-[a-zA-Z0-9]{20,}', '[REDACTED: OpenAI API Key]'),
    (r'sk-proj-[a-zA-Z0-9\-_]{50,}', '[REDACTED: OpenAI Project Key]'),
    
    # Anthropic
    (r'sk-ant-[a-zA-Z0-9\-_]{20,}', '[REDACTED: Anthropic API Key]'),
    
    # xAI
    (r'xai-[a-zA-Z0-9]{20,}', '[REDACTED: xAI API Key]'),
    
    # Google
    (r'AIza[a-zA-Z0-9\-_]{35}', '[REDACTED: Google API Key]'),
    
    # AWS
    (r'AKIA[0-9A-Z]{16}', '[REDACTED: AWS Access Key]'),
    
    # GitHub
    (r'ghp_[a-zA-Z0-9]{36,}', '[REDACTED: GitHub PAT]'),
    (r'github_pat_[a-zA-Z0-9_]{20,}', '[REDACTED: GitHub PAT]'),
    (r'gho_[a-zA-Z0-9]{36,}', '[REDACTED: GitHub OAuth]'),
    
    # GitLab
    (r'glpat-[a-zA-Z0-9\-_]{20,}', '[REDACTED: GitLab Token]'),
    
    # Slack
    (r'xox[baprs]-[a-zA-Z0-9\-]{10,}', '[REDACTED: Slack Token]'),
    
    # Stripe
    (r'sk_live_[a-zA-Z0-9]{24,}', '[REDACTED: Stripe Live Key]'),
    (r'sk_test_[a-zA-Z0-9]{24,}', '[REDACTED: Stripe Test Key]'),
    
    # NPM
    (r'npm_[a-zA-Z0-9]{36}', '[REDACTED: NPM Token]'),
    
    # Supabase
    (r'supabase_[a-zA-Z0-9_-]{20,}', '[REDACTED: Supabase Key]'),
    (r'sb_[a-zA-Z0-9_-]{20,}', '[REDACTED: Supabase Key]'),
    
    # Bearer tokens and JWTs
    (r'Bearer\s+[a-zA-Z0-9._\-]{20,}', '[REDACTED: Bearer Token]'),
    (r'eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*', '[REDACTED: JWT Token]'),
    
    # Private keys and certificates
    (r'-----BEGIN\s+(RSA\s+|EC\s+|DSA\s+|OPENSSH\s+|PGP\s+)?PRIVATE\s+KEY(\s+BLOCK)?-----[\s\S]*?-----END\s+(RSA\s+|EC\s+|DSA\s+|OPENSSH\s+|PGP\s+)?PRIVATE\s+KEY(\s+BLOCK)?-----', '[REDACTED: Private Key]'),
    (r'-----BEGIN\s+CERTIFICATE-----[\s\S]*?-----END\s+CERTIFICATE-----', '[REDACTED: Certificate]'),
    
    # Database URLs
    (r'postgres(ql)?://[^\s]+', '[REDACTED: PostgreSQL URL]'),
    (r'mysql://[^\s]+', '[REDACTED: MySQL URL]'),
    (r'mongodb(\+srv)?://[^\s]+', '[REDACTED: MongoDB URL]'),
    (r'redis://[^\s]+', '[REDACTED: Redis URL]'),
    (r'amqp://[^\s]+', '[REDACTED: AMQP URL]'),
    
    # Credentials in URLs
    (r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}:[^\s@]+@', '[REDACTED: Credential in URL]'),
    
    # Generic patterns (case-insensitive) - must come last
    (r'password\s*[=:]\s*["\']?[^\s"\']{8,}["\']?', '[REDACTED: Password]', re.IGNORECASE),
    (r'api[_-]?key\s*[=:]\s*["\']?[a-zA-Z0-9_-]{16,}["\']?', '[REDACTED: API Key]', re.IGNORECASE),
    (r'secret\s*[=:]\s*["\']?[a-zA-Z0-9_-]{16,}["\']?', '[REDACTED: Secret]', re.IGNORECASE),
    (r'token\s*[=:]\s*["\']?[a-zA-Z0-9_.-]{20,}["\']?', '[REDACTED: Token]', re.IGNORECASE),
    (r'auth_token\s*[=:]\s*["\']?[a-zA-Z0-9_.-]{20,}["\']?', '[REDACTED: Auth Token]', re.IGNORECASE),
    (r'access_token\s*[=:]\s*["\']?[a-zA-Z0-9_.-]{20,}["\']?', '[REDACTED: Access Token]', re.IGNORECASE),
    (r'refresh_token\s*[=:]\s*["\']?[a-zA-Z0-9_.-]{20,}["\']?', '[REDACTED: Refresh Token]', re.IGNORECASE),
]


def redact_secrets(text):
    """Redact sensitive information from text.
    
    Args:
        text: The text to redact secrets from.
        
    Returns:
        Text with secrets replaced by [REDACTED: ...] placeholders.
    """
    if not text:
        return text
    
    for pattern in SECRET_PATTERNS:
        try:
            if len(pattern) == 3:
                regex, replacement, flags = pattern
                text = re.sub(regex, replacement, text, flags=flags)
            else:
                regex, replacement = pattern
                text = re.sub(regex, replacement, text)
        except Exception:
            # Skip patterns that fail to compile/match
            pass
    
    return text


def format_code_block(code, language=""):
    """Format code as a markdown code block.
    
    Args:
        code: The code content.
        language: Optional language identifier for syntax highlighting.
        
    Returns:
        Markdown-formatted code block string.
    """
    if not code:
        return ""
    lang = language.lower() if language else ""
    return f"\n```{lang}\n{code}\n```\n"


def to_kebab_case(text):
    """Convert text to kebab-case.
    
    Args:
        text: Input text to convert.
        
    Returns:
        Kebab-case version of the text.
    """
    # Replace spaces and underscores with hyphens
    text = re.sub(r'[\s_]+', '-', text)
    # Convert to lowercase
    text = text.lower()
    # Remove any characters that aren't alphanumeric or hyphens
    text = re.sub(r'[^a-z0-9-]', '', text)
    # Remove multiple consecutive hyphens
    text = re.sub(r'-+', '-', text)
    # Remove leading/trailing hyphens
    text = text.strip('-')
    return text


def get_obsidian_vault():
    """Get the Obsidian vault path.
    
    Returns:
        Path to the Obsidian vault.
    """
    # Could be extended to read from a config file
    return DEFAULT_OBSIDIAN_VAULT
