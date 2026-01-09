#!/usr/bin/env python3
"""
Common utilities for AI Sessions Sync
======================================
Cross-platform support for macOS, Linux, and Windows.
"""

import os
import re
import platform
from pathlib import Path

HOME = Path.home()

def get_obsidian_vault():
    """
    Auto-detect Obsidian vault location across platforms.
    
    Checks these locations in order:
    1. OBSIDIAN_VAULT environment variable
    2. ~/.aisync.conf file
    3. Common Obsidian vault locations
    
    Returns: Path to vault, or None if not found
    """
    # 1. Check environment variable
    env_vault = os.environ.get('OBSIDIAN_VAULT')
    if env_vault and Path(env_vault).exists():
        return Path(env_vault)
    
    # 2. Check config file
    config_file = HOME / ".aisync.conf"
    if config_file.exists():
        try:
            content = config_file.read_text()
            for line in content.split('\n'):
                if line.startswith('OBSIDIAN_VAULT='):
                    vault_path = line.split('=', 1)[1].strip().strip('"\'')
                    vault_path = Path(vault_path).expanduser()
                    if vault_path.exists():
                        return vault_path
        except:
            pass
    
    # 3. Check common locations
    system = platform.system()
    
    if system == "Darwin":  # macOS
        common_paths = [
            HOME / "Library/Mobile Documents/iCloud~md~obsidian/Documents",
            HOME / "Documents/Obsidian",
            HOME / "Obsidian",
            HOME / "Documents/obsidian",
        ]
    elif system == "Linux":
        common_paths = [
            HOME / "Documents/Obsidian",
            HOME / "Obsidian",
            HOME / "obsidian",
            HOME / ".obsidian",
            HOME / "Documents/obsidian",
        ]
    elif system == "Windows":
        common_paths = [
            HOME / "Documents/Obsidian",
            HOME / "Obsidian",
            Path("C:/Users") / os.environ.get('USERNAME', '') / "Documents/Obsidian",
            HOME / "OneDrive/Documents/Obsidian",
        ]
    else:
        common_paths = [HOME / "Obsidian", HOME / "Documents/Obsidian"]
    
    # Look for .obsidian folder (indicates a vault)
    for base_path in common_paths:
        if base_path.exists():
            # Check if it's a vault directly
            if (base_path / ".obsidian").exists():
                return base_path
            # Check subdirectories
            try:
                for subdir in base_path.iterdir():
                    if subdir.is_dir() and (subdir / ".obsidian").exists():
                        return subdir
            except PermissionError:
                continue
    
    # Default fallback
    default = HOME / "Documents/Obsidian/ai-sessions-vault"
    print(f"⚠️  No Obsidian vault found. Using default: {default}")
    print(f"   Set OBSIDIAN_VAULT env var or create ~/.aisync.conf with:")
    print(f'   OBSIDIAN_VAULT="/path/to/your/vault"')
    return default


def get_vscode_global_storage():
    """Get VS Code global storage path for the current platform."""
    system = platform.system()
    
    if system == "Darwin":
        return HOME / "Library/Application Support/Code/User/globalStorage"
    elif system == "Linux":
        return HOME / ".config/Code/User/globalStorage"
    elif system == "Windows":
        appdata = Path(os.environ.get('APPDATA', HOME / 'AppData/Roaming'))
        return appdata / "Code/User/globalStorage"
    else:
        return HOME / ".config/Code/User/globalStorage"


def get_cursor_global_storage():
    """Get Cursor global storage path for the current platform."""
    system = platform.system()
    
    if system == "Darwin":
        return HOME / "Library/Application Support/Cursor/User/globalStorage"
    elif system == "Linux":
        return HOME / ".config/Cursor/User/globalStorage"
    elif system == "Windows":
        appdata = Path(os.environ.get('APPDATA', HOME / 'AppData/Roaming'))
        return appdata / "Cursor/User/globalStorage"
    else:
        return HOME / ".config/Cursor/User/globalStorage"


# Secret patterns to redact (shared across all sync scripts)
SECRET_PATTERNS = [
    # API Keys
    (r'sk-[a-zA-Z0-9]{20,}', '[REDACTED: OpenAI API Key]'),
    (r'sk-ant-[a-zA-Z0-9-]{20,}', '[REDACTED: Anthropic API Key]'),
    (r'sk-proj-[a-zA-Z0-9-]{20,}', '[REDACTED: OpenAI Project Key]'),
    (r'AIza[a-zA-Z0-9_-]{35}', '[REDACTED: Google API Key]'),
    (r'ya29\.[a-zA-Z0-9_-]+', '[REDACTED: Google OAuth Token]'),
    (r'sgp_[a-zA-Z0-9_-]{40,}', '[REDACTED: Sourcegraph Token]'),
    
    # GitHub
    (r'ghp_[a-zA-Z0-9]{36,}', '[REDACTED: GitHub PAT]'),
    (r'gho_[a-zA-Z0-9]{36,}', '[REDACTED: GitHub OAuth]'),
    (r'ghs_[a-zA-Z0-9]{36,}', '[REDACTED: GitHub App Token]'),
    (r'ghu_[a-zA-Z0-9]{36,}', '[REDACTED: GitHub User Token]'),
    (r'github_pat_[a-zA-Z0-9_]{22,}', '[REDACTED: GitHub PAT v2]'),
    
    # AWS
    (r'AKIA[0-9A-Z]{16}', '[REDACTED: AWS Access Key]'),
    (r'aws_secret_access_key\s*=\s*[^\s]+', '[REDACTED: AWS Secret]'),
    
    # Generic tokens
    (r'Bearer\s+[a-zA-Z0-9._-]{20,}', '[REDACTED: Bearer Token]'),
    (r'eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*', '[REDACTED: JWT Token]'),
    (r'xox[baprs]-[a-zA-Z0-9-]+', '[REDACTED: Slack Token]'),
    
    # Database URLs
    (r'postgres://[^\s]+', '[REDACTED: Database URL]'),
    (r'mysql://[^\s]+', '[REDACTED: Database URL]'),
    (r'mongodb(\+srv)?://[^\s]+', '[REDACTED: MongoDB URL]'),
    (r'redis://[^\s]+', '[REDACTED: Redis URL]'),
    
    # Private keys
    (r'-----BEGIN (?:RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----', '[REDACTED: Private Key]'),
    
    # Passwords in URLs
    (r'://[^:]+:[^@]+@', '://[REDACTED]@'),
]


def redact_secrets(text):
    """Redact sensitive information from text."""
    if not text:
        return text
    for pattern, replacement in SECRET_PATTERNS:
        text = re.sub(pattern, replacement, text)
    return text
