"""Rule: detect public functions / methods missing return type annotations."""

from __future__ import annotations

import ast
from pathlib import Path

from prefact.models import Fix, Issue, Severity, ValidationResult
from prefact.rules import BaseRule, register


@register
class MissingReturnType(BaseRule):
    rule_id = "missing-return-type"
    description = "Detect public functions missing return type annotations (scan-only)."

    def scan_file(self, path: Path, source: str) -> list[Issue]:
        issues: list[Issue] = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return issues

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("_"):
                    continue  # skip private
                if node.returns is None:
                    issues.append(
                        Issue(
                            rule_id=self.rule_id, file=path,
                            line=node.lineno, col=node.col_offset,
                            message=f"Function '{node.name}' missing return type annotation.",
                            severity=Severity.INFO,
                            original=node.name,
                        )
                    )
        return issues

    def fix(self, path: Path, source: str, issues: list[Issue]) -> tuple[str, list[Fix]]:
        return source, []  # cannot infer types automatically

    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        return ValidationResult(file=path, passed=True, checks=["no_auto_fix"])
