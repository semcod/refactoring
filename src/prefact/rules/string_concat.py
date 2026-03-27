"""Rule: detect string concatenation with + that could use f-strings.

Flags patterns like:
    "Hello " + name + "!"
and suggests:
    f"Hello {name}!"

Scan-only – no auto-fix (too many edge cases with nested quotes).
"""

import ast
from pathlib import Path

from prefact.models import Fix, Issue, Severity, ValidationResult
from prefact.rules import BaseRule, register


def _is_str_concat(node: ast.BinOp) -> bool:
    """Check if node is a string + concatenation mixing literals and names."""
    if not isinstance(node.op, ast.Add):
        return False
    parts = _flatten_add(node)
    has_str = any(isinstance(p, ast.Constant) and isinstance(p.value, str) for p in parts)
    has_name = any(isinstance(p, (ast.Name, ast.Attribute, ast.Call)) for p in parts)
    return has_str and has_name


def _flatten_add(node: ast.expr) -> list[ast.expr]:
    """Flatten nested BinOp(Add) into a list of operands."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return f"{_flatten_add(node.left)}{_flatten_add(node.right)}"
    return [node]


@register
class StringConcatToFstring(BaseRule):
    rule_id = "string-concat"
    description = "Detect string concatenation that could be f-strings (scan-only)."

    def scan_file(self, path: Path, source: str) -> list[Issue]:
        issues: list[Issue] = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return issues
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp) and _is_str_concat(node):
                issues.append(
                    Issue(
                        rule_id=self.rule_id, file=path,
                        line=node.lineno, col=node.col_offset,
                        message="String concatenation could use f-string.",
                        severity=Severity.INFO,
                    )
                )
        return issues

    def fix(self, path: Path, source: str, issues: list[Issue]) -> tuple[str, list[Fix]]:
        return source, []  # too many edge cases for safe auto-fix

    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        return ValidationResult(file=path, passed=True, checks=["no_auto_fix"])
