"""Rule: detect print() statements that may be debug leftovers.

Flags bare ``print()`` calls. Configurable: ignore files matching patterns
(e.g. CLI modules, scripts).
"""

from __future__ import annotations

import ast
from pathlib import Path

from prefact.models import Fix, Issue, Severity, ValidationResult
from prefact.rules import BaseRule, register


@register
class PrintStatements(BaseRule):
    rule_id = "print-statements"
    description = "Detect print() calls that may be leftover debug statements."

    def scan_file(self, path: Path, source: str) -> list[Issue]:
        issues: list[Issue] = []
        # Skip files that are explicitly CLI / scripts
        ignore = self.config.rule_options(self.rule_id).get("ignore_patterns", [])
        rel = str(path)
        for pat in ignore:
            if pat in rel:
                return issues

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return issues

        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "print"
            ):
                issues.append(
                    Issue(
                        rule_id=self.rule_id, file=path,
                        line=node.lineno, col=node.col_offset,
                        message="print() call – consider using logging instead.",
                        severity=Severity.INFO,
                    )
                )
        return issues

    def fix(self, path: Path, source: str, issues: list[Issue]) -> tuple[str, list[Fix]]:
        return source, []  # removing prints blindly is risky

    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        return ValidationResult(file=path, passed=True, checks=["no_auto_fix"])
