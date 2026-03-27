"""Rule: detect unsorted import blocks (stdlib → third-party → local)."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

from prefact.models import Fix, Issue, Severity, ValidationResult
from prefact.rules import BaseRule, register

_STDLIB = set(sys.stdlib_module_names) if hasattr(sys, "stdlib_module_names") else set()


def _sort_key(node: ast.stmt) -> tuple[int, str]:
    if isinstance(node, ast.Import):
        name = node.names[0].name
    elif isinstance(node, ast.ImportFrom):
        name = node.module or ""
    else:
        return (99, "")
    top = name.split(".")[0]
    group = 0 if top in _STDLIB else (2 if top.startswith("_") else 1)
    return (group, name.lower())


@register
class SortedImports(BaseRule):
    rule_id = "sorted-imports"
    description = "Detect unsorted import blocks (report only)."

    def scan_file(self, path: Path, source: str) -> list[Issue]:
        issues: list[Issue] = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return issues
        imports = [n for n in ast.iter_child_nodes(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
        if len(imports) < 2:
            return issues
        keys = [_sort_key(n) for n in imports]
        if keys != sorted(keys):
            issues.append(
                Issue(
                    rule_id=self.rule_id, file=path,
                    line=imports[0].lineno, col=0,
                    message="Import block is not sorted (stdlib → third-party → local).",
                    severity=Severity.INFO,
                )
            )
        return issues

    def fix(self, path: Path, source: str, issues: list[Issue]) -> tuple[str, list[Fix]]:
        return source, []  # delegate to isort / ruff

    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        return ValidationResult(file=path, passed=True, checks=["no_auto_fix"])
