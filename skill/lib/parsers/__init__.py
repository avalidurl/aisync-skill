"""
Session parsers for various AI coding tools.
"""

from .base import BaseParser
from .claude import ClaudeCodeParser
from .codex import CodexParser
from .cursor import CursorParser
from .aider import AiderParser
from .cline import ClineParser
from .gemini import GeminiCLIParser
from .continue_dev import ContinueParser
from .copilot import CopilotParser
from .roo import RooCodeParser
from .windsurf import WindsurfParser
from .zed import ZedAIParser
from .amp import AmpParser
from .opencode import OpenCodeParser
from .openrouter import OpenRouterParser

from typing import Dict, Type
from ..models import Provider

# Registry of all parsers
PARSERS: Dict[Provider, Type[BaseParser]] = {
    Provider.CLAUDE_CODE: ClaudeCodeParser,
    Provider.CODEX: CodexParser,
    Provider.CURSOR: CursorParser,
    Provider.AIDER: AiderParser,
    Provider.CLINE: ClineParser,
    Provider.GEMINI_CLI: GeminiCLIParser,
    Provider.CONTINUE: ContinueParser,
    Provider.COPILOT: CopilotParser,
    Provider.ROO_CODE: RooCodeParser,
    Provider.WINDSURF: WindsurfParser,
    Provider.ZED_AI: ZedAIParser,
    Provider.AMP: AmpParser,
    Provider.OPENCODE: OpenCodeParser,
    Provider.OPENROUTER: OpenRouterParser,
}


def get_parser(provider: Provider, home_dir: str = None) -> BaseParser:
    """Get parser instance for a provider."""
    parser_class = PARSERS.get(provider)
    if not parser_class:
        raise ValueError(f"No parser for provider: {provider}")
    return parser_class(home_dir)


def get_all_parsers(home_dir: str = None) -> Dict[Provider, BaseParser]:
    """Get all parser instances."""
    return {p: cls(home_dir) for p, cls in PARSERS.items()}


__all__ = [
    'BaseParser',
    'ClaudeCodeParser',
    'CodexParser',
    'CursorParser',
    'AiderParser',
    'ClineParser',
    'GeminiCLIParser',
    'ContinueParser',
    'CopilotParser',
    'RooCodeParser',
    'WindsurfParser',
    'ZedAIParser',
    'AmpParser',
    'OpenCodeParser',
    'OpenRouterParser',
    'PARSERS',
    'get_parser',
    'get_all_parsers',
]
