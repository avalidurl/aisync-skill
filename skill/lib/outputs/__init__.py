"""
Output plugins for AI sessions.
"""

from .base import BaseOutput
from .obsidian import ObsidianOutput
from .json_output import JSONOutput, JSONLOutput
from .html import HTMLOutput
from .sqlite import SQLiteOutput

from typing import Dict, Type

# Registry of output plugins
OUTPUTS: Dict[str, Type[BaseOutput]] = {
    'obsidian': ObsidianOutput,
    'json': JSONOutput,
    'jsonl': JSONLOutput,
    'html': HTMLOutput,
    'sqlite': SQLiteOutput,
}


def get_output(name: str, output_dir, **config) -> BaseOutput:
    """Get output plugin instance."""
    output_class = OUTPUTS.get(name)
    if not output_class:
        raise ValueError(f"Unknown output: {name}. Available: {list(OUTPUTS.keys())}")
    return output_class(output_dir, **config)


def list_outputs() -> Dict[str, str]:
    """List available outputs with descriptions."""
    return {name: cls.description for name, cls in OUTPUTS.items()}


__all__ = [
    'BaseOutput',
    'ObsidianOutput',
    'JSONOutput',
    'JSONLOutput',
    'HTMLOutput',
    'SQLiteOutput',
    'OUTPUTS',
    'get_output',
    'list_outputs',
]
