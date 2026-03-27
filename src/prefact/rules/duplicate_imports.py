"""Rule: detect and remove duplicate imports."""


import ast
from pathlib import Path

from prefact.models import Fix, Issue, Severity, ValidationResult
from prefact.rules import BaseRule, register


@register
class DuplicateImports(BaseRule):
    rule_id = "duplicate-imports"
    description = "Detect the same name being imported multiple times."

    def scan_file(self, path: Path, source: str) -> list[Issue]:
        issues: list[Issue] = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return issues

        seen: dict[str, int] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    name = alias.asname or alias.name
                    if name in seen:
                        issues.append(
                            Issue(
                                rule_id=self.rule_id, file=path,
                                line=node.lineno, col=node.col_offset,
                                message=f"Duplicate import: '{name}' (first at line {seen[name]})",
                                severity=Severity.WARNING, original=name,
                                meta={"first_line": seen[name]},
                            )
                        )
                    else:
                        seen[name] = node.lineno
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name.split(".")[0]
                    if name in seen:
                        issues.append(
                            Issue(
                                rule_id=self.rule_id, file=path,
                                line=node.lineno, col=node.col_offset,
                                message=f"Duplicate import: '{name}' (first at line {seen[name]})",
                                severity=Severity.WARNING, original=name,
                                meta={"first_line": seen[name]},
                            )
                        )
                    else:
                        seen[name] = node.lineno
        return issues

    def fix(self, path: Path, source: str, issues: list[Issue]) -> tuple[str, list[Fix]]:
        if not issues:
            return source, []
        dup_lines: set[int] = {i.line for i in issues}
        lines = source.splitlines(keepends=True)
        new_lines = [l for idx, l in enumerate(lines, 1) if idx not in dup_lines]
        fixes = [
            Fix(issue=iss, file=path, original_code=lines[iss.line - 1].rstrip(), fixed_code="", applied=True)
            for iss in issues if iss.line <= len(lines)
        ]
        return "".join(new_lines), fixes

    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        checks, errors = [], []
        try:
            ast.parse(fixed)
            checks.append("syntax_valid")
        except SyntaxError as exc:
            errors.append(f"SyntaxError: {exc}")
        return ValidationResult(file=path, passed=not errors, checks=checks, errors=errors)
