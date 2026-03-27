"""Fixer – applies fixes suggested by rules."""

from __future__ import annotations

import shutil
from pathlib import Path

from prefact.config import Config
from prefact.models import Fix, Issue
from prefact.rules import BaseRule, get_all_rules


class Fixer:
    def __init__(self, config: Config) -> None:
        self.config = config
        self._rules: dict[str, BaseRule] = {}
        for rule_id, rule_cls in get_all_rules().items():
            if config.rule_enabled(rule_id):
                self._rules[rule_id] = rule_cls(config)

    def fix_file(
        self, path: Path, issues: list[Issue], *, dry_run: bool = False,
    ) -> tuple[str, list[Fix]]:
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return "", []

        all_fixes: list[Fix] = []
        by_rule: dict[str, list[Issue]] = {}
        for iss in issues:
            by_rule.setdefault(iss.rule_id, []).append(iss)

        for rule_id, rule_issues in by_rule.items():
            rule = self._rules.get(rule_id)
            if rule is None:
                continue
            source, fixes = rule.fix(path, source, rule_issues)
            all_fixes.extend(fixes)

        if not dry_run and all_fixes:
            if self.config.backup:
                shutil.copy2(path, path.with_suffix(f"{path.suffix}.bak"))
            path.write_text(source, encoding="utf-8")

        return source, all_fixes
