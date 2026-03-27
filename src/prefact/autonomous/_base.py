"""Base utilities for autonomous modules."""

from pathlib import Path
from typing import Any, Dict, List, Tuple

from rich.console import Console

from prefact import __version__

# Shared console instance
console = Console()

# Constants for code analysis
MIN_CODE_SIZE = 50
HASH_BLOCK_SIZE = 65536


class BaseManager:
    """Base class for autonomous managers."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.refact_config_path = project_root / "prefact.yaml"
        self.planfile_path = project_root / "planfile.yaml"
        self.todo_path = project_root / "TODO.md"
        self.changelog_path = project_root / "CHANGELOG.md"
        self.examples_dir = project_root / "examples"
