"""Scanner – walks the project tree and collects issues."""

from __future__ import annotations

import fnmatch
from pathlib import Path

from prefact.config import Config
from prefact.models import Issue
from prefact.rules import BaseRule, get_all_rules


class Scanner:
    """Discovers Python files and runs all enabled rules against them."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self._rules: list[BaseRule] = []
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
        rel = str(path.relative_to(self.config.project_root))
        return any(fnmatch.fnmatch(rel, pat) for pat in self.config.exclude)
