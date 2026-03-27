"""Validator – runs post-fix checks to ensure nothing is broken."""

from __future__ import annotations

from pathlib import Path

from prefact.config import Config
from prefact.models import Issue, ValidationResult
from prefact.rules import BaseRule, get_all_rules


class Validator:
    def __init__(self, config: Config) -> None:
        self.config = config
        self._rules: dict[str, BaseRule] = {}
        for rule_id, rule_cls in get_all_rules().items():
            if config.rule_enabled(rule_id):
                self._rules[rule_id] = rule_cls(config)

    def validate_file(
        self, path: Path, original_source: str, fixed_source: str, issues: list[Issue],
    ) -> list[ValidationResult]:
        results: list[ValidationResult] = []
        rule_ids = {i.rule_id for i in issues}
        for rule_id in rule_ids:
            rule = self._rules.get(rule_id)
            if rule is None:
                continue
            results.append(rule.validate(path, original_source, fixed_source))
        return results
