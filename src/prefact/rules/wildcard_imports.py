"""Rule: detect wildcard ``from x import *`` statements."""

import ast
from pathlib import Path

from prefact.models import Fix, Issue, Severity, ValidationResult
from prefact.rules import BaseRule, register


@register
class WildcardImports(BaseRule):
    rule_id = "wildcard-imports"
    description = "Detect 'from x import *' statements (scan-only, no auto-fix)."

    def scan_file(self, path: Path, source: str) -> list[Issue]:
        issues: list[Issue] = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return issues
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name == "*":
                        module = node.module or ""
                        issues.append(
                            Issue(
                                rule_id=self.rule_id, file=path,
                                line=node.lineno, col=node.col_offset,
                                message=f"Wildcard import: 'from {module} import *'",
                                severity=Severity.ERROR,
                                original=f"from {module} import *",
                            )
                        )
        return issues

    def fix(self, path: Path, source: str, issues: list[Issue]) -> tuple[str, list[Fix]]:
        return source, []  # cannot safely auto-fix without runtime info

    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        return ValidationResult(file=path, passed=True, checks=["no_auto_fix"])
