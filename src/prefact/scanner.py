"""Scanner – walks the project tree and collects issues."""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path

from prefact.config import Config
from prefact.models import Issue
from prefact.rules import BaseRule, get_all_rules


def _load_gitignore(root: Path) -> list[str]:
    """Load .gitignore patterns from project root."""
    gitignore_path = root / ".gitignore"
    patterns = []
    if gitignore_path.exists():
        try:
            with open(gitignore_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith("#"):
                        patterns.append(line)
        except (OSError, UnicodeDecodeError):
            pass
    return patterns


def _match_gitignore_pattern(path: str, pattern: str) -> bool:
    """Match a path against a gitignore-style pattern."""
    # Handle directory-only patterns (ending with /)
    if pattern.endswith("/"):
        pattern = pattern.rstrip("/")
        if not path.endswith("/"):
            path = path + "/"
    
    # Handle negation patterns (starting with !)
    if pattern.startswith("!"):
        return False  # Negation handled separately
    
    # Convert pattern to fnmatch format
    # ** matches any number of directories
    if "**" in pattern:
        # Split path and pattern
        path_parts = path.split("/")
        pattern_parts = pattern.split("/")
        
        # Handle ** at start
        if pattern_parts[0] == "**":
            # Match remaining pattern anywhere in path
            remaining = "/".join(pattern_parts[1:])
            # Try matching at each position
            for i in range(len(path_parts)):
                subpath = "/".join(path_parts[i:])
                if fnmatch.fnmatch(subpath, remaining):
                    return True
            return fnmatch.fnmatch(path, remaining)
        else:
            # Standard fnmatch for simple patterns
            return fnmatch.fnmatch(path, pattern)
    else:
        # Standard fnmatch for simple patterns
        # Also check if pattern matches any path component
        if fnmatch.fnmatch(path, pattern):
            return True
        # Check if pattern matches the basename
        if fnmatch.fnmatch(os.path.basename(path), pattern):
            return True
        # Check if pattern with **/ prefix matches
        if fnmatch.fnmatch(path, f"*/{pattern}") or fnmatch.fnmatch(path, f"**/{pattern}"):
            return True
        return False


class Scanner:
    """Discovers Python files and runs all enabled rules against them."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self._rules: list[BaseRule] = []
        # Load gitignore patterns
        self._gitignore_patterns = _load_gitignore(config.project_root)
        # Combine with config exclude patterns
        self._exclude_patterns = list(config.exclude) + self._gitignore_patterns
        for rule_id, rule_cls in get_all_rules().items():
            if config.rule_enabled(rule_id):
                self._rules.append(rule_cls(config))

    def collect_files(self) -> list[Path]:
        root = self.config.project_root
        files: list[Path] = []
        for pattern in self.config.include:
            for p in root.glob(pattern):
                if p.is_file() and not self._excluded(p):
                    files.append(p)
        return sorted(set(files))

    def scan(self, files: list[Path] | None = None) -> dict[Path, list[Issue]]:
        if files is None:
            files = self.collect_files()
        results: dict[Path, list[Issue]] = {}
        for path in files:
            try:
                source = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            file_issues: list[Issue] = []
            for rule in self._rules:
                file_issues.extend(rule.scan_file(path, source))
            if file_issues:
                results[path] = file_issues
        return results

    def _excluded(self, path: Path) -> bool:
        """Check if a path should be excluded based on patterns."""
        rel = str(path.relative_to(self.config.project_root))
        # Also check the full path string for pattern matching
        path_str = str(path)
        
        for pat in self._exclude_patterns:
            # Skip empty patterns
            if not pat:
                continue
                
            # Check if pattern matches the relative path
            if _match_gitignore_pattern(rel, pat):
                return True
            # Check if pattern matches with leading components
            if _match_gitignore_pattern(rel, f"**/{pat}"):
                return True
            # Check full path for virtual env patterns
            if ".venv" in pat and ".venv" in path_str:
                return True
            if "venv" in pat and "venv" in path_str:
                return True
            if "site-packages" in path_str:
                return True
            if "__pycache__" in path_str:
                return True
            if "node_modules" in path_str:
                return True
                
        return False
