"""
Secret redaction module.
Detects and redacts sensitive information from session content.
"""

import re
from typing import List, Tuple, Dict, Set
from dataclasses import dataclass


@dataclass
class RedactionResult:
    """Result of redaction operation."""
    original_length: int
    redacted_length: int
    redactions_count: int
    redaction_types: Dict[str, int]  # type -> count


# Secret patterns with categories
SECRET_PATTERNS: List[Tuple[str, str, str]] = [
    # (pattern, replacement, category)
    
    # API Keys - OpenAI
    (r'sk-[a-zA-Z0-9]{20,}', '[REDACTED: OpenAI API Key]', 'api_key'),
    (r'sk-proj-[a-zA-Z0-9-]{20,}', '[REDACTED: OpenAI Project Key]', 'api_key'),
    
    # API Keys - Anthropic
    (r'sk-ant-[a-zA-Z0-9-]{20,}', '[REDACTED: Anthropic API Key]', 'api_key'),
    
    # API Keys - Google
    (r'AIza[a-zA-Z0-9_-]{35}', '[REDACTED: Google API Key]', 'api_key'),
    (r'ya29\.[a-zA-Z0-9_-]+', '[REDACTED: Google OAuth Token]', 'oauth'),
    
    # API Keys - Sourcegraph
    (r'sgp_[a-zA-Z0-9_-]{40,}', '[REDACTED: Sourcegraph Token]', 'api_key'),
    
    # GitHub
    (r'ghp_[a-zA-Z0-9]{36,}', '[REDACTED: GitHub PAT]', 'github'),
    (r'gho_[a-zA-Z0-9]{36,}', '[REDACTED: GitHub OAuth]', 'github'),
    (r'ghs_[a-zA-Z0-9]{36,}', '[REDACTED: GitHub App Token]', 'github'),
    (r'ghu_[a-zA-Z0-9]{36,}', '[REDACTED: GitHub User Token]', 'github'),
    (r'github_pat_[a-zA-Z0-9_]{22,}', '[REDACTED: GitHub PAT v2]', 'github'),
    
    # AWS
    (r'AKIA[0-9A-Z]{16}', '[REDACTED: AWS Access Key]', 'aws'),
    (r'(?i)aws_secret_access_key\s*[=:]\s*[^\s]+', '[REDACTED: AWS Secret]', 'aws'),
    (r'(?i)aws_session_token\s*[=:]\s*[^\s]+', '[REDACTED: AWS Session Token]', 'aws'),
    
    # Azure
    (r'(?i)azure[_-]?(?:storage|api|key)[_-]?(?:key|secret)?\s*[=:]\s*[^\s]{20,}', '[REDACTED: Azure Key]', 'azure'),
    
    # Generic tokens
    (r'Bearer\s+[a-zA-Z0-9._-]{20,}', '[REDACTED: Bearer Token]', 'bearer'),
    (r'eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*', '[REDACTED: JWT Token]', 'jwt'),
    (r'xox[baprs]-[a-zA-Z0-9-]+', '[REDACTED: Slack Token]', 'slack'),
    
    # Stripe
    (r'sk_live_[a-zA-Z0-9]{24,}', '[REDACTED: Stripe Live Key]', 'stripe'),
    (r'sk_test_[a-zA-Z0-9]{24,}', '[REDACTED: Stripe Test Key]', 'stripe'),
    (r'pk_live_[a-zA-Z0-9]{24,}', '[REDACTED: Stripe Pub Key]', 'stripe'),
    
    # Database URLs
    (r'postgres(?:ql)?://[^\s]+', '[REDACTED: PostgreSQL URL]', 'database'),
    (r'mysql://[^\s]+', '[REDACTED: MySQL URL]', 'database'),
    (r'mongodb(?:\+srv)?://[^\s]+', '[REDACTED: MongoDB URL]', 'database'),
    (r'redis://[^\s]+', '[REDACTED: Redis URL]', 'database'),
    (r'amqp://[^\s]+', '[REDACTED: AMQP URL]', 'database'),
    
    # Private keys
    (r'-----BEGIN (?:RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----', 
     '[REDACTED: Private Key Block]', 'private_key'),
    
    # Passwords in URLs
    (r'://([^:]+):([^@]+)@', '://[USER]:[REDACTED]@', 'password_url'),
    
    # Generic password patterns
    (r'(?i)(?:password|passwd|pwd|secret|token|api[_-]?key)\s*[=:]\s*["\']?([^"\'\s]{8,})["\']?', 
     '[REDACTED: Credential]', 'credential'),
    
    # SSH keys
    (r'ssh-(?:rsa|ed25519|ecdsa)\s+[A-Za-z0-9+/]+[=]{0,2}', '[REDACTED: SSH Public Key]', 'ssh'),
    
    # Webhook URLs
    (r'https://hooks\.slack\.com/[^\s]+', '[REDACTED: Slack Webhook]', 'webhook'),
    (r'https://discord\.com/api/webhooks/[^\s]+', '[REDACTED: Discord Webhook]', 'webhook'),
]


class SecretRedactor:
    """Redacts secrets from text."""
    
    def __init__(self, custom_patterns: List[Tuple[str, str, str]] = None):
        """
        Initialize redactor.
        
        Args:
            custom_patterns: Additional patterns as (regex, replacement, category)
        """
        self.patterns = SECRET_PATTERNS.copy()
        if custom_patterns:
            self.patterns.extend(custom_patterns)
        
        # Compile patterns for performance
        self._compiled = [(re.compile(p), r, c) for p, r, c in self.patterns]
    
    def redact(self, text: str) -> Tuple[str, RedactionResult]:
        """
        Redact secrets from text.
        
        Args:
            text: Text to redact
            
        Returns:
            Tuple of (redacted_text, result)
        """
        if not text:
            return text, RedactionResult(0, 0, 0, {})
        
        original_length = len(text)
        redaction_counts: Dict[str, int] = {}
        total_redactions = 0
        
        for pattern, replacement, category in self._compiled:
            matches = pattern.findall(text)
            if matches:
                count = len(matches)
                redaction_counts[category] = redaction_counts.get(category, 0) + count
                total_redactions += count
                text = pattern.sub(replacement, text)
        
        result = RedactionResult(
            original_length=original_length,
            redacted_length=len(text),
            redactions_count=total_redactions,
            redaction_types=redaction_counts
        )
        
        return text, result
    
    def redact_simple(self, text: str) -> str:
        """Simple redaction without result details."""
        if not text:
            return text
        
        for pattern, replacement, _ in self._compiled:
            text = pattern.sub(replacement, text)
        
        return text
    
    def detect_secrets(self, text: str) -> List[Dict[str, str]]:
        """
        Detect secrets without redacting.
        
        Returns:
            List of detected secrets with type and position
        """
        if not text:
            return []
        
        secrets = []
        for pattern, _, category in self._compiled:
            for match in pattern.finditer(text):
                secrets.append({
                    'category': category,
                    'start': match.start(),
                    'end': match.end(),
                    'preview': text[max(0, match.start()-10):match.start()] + '...' + text[match.end():min(len(text), match.end()+10)]
                })
        
        return secrets


# Default redactor instance
default_redactor = SecretRedactor()


def redact_secrets(text: str) -> str:
    """Convenience function for simple redaction."""
    return default_redactor.redact_simple(text)
