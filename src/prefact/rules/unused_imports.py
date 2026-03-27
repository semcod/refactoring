"""Rule: detect and remove unused imports."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Optional

from prefact.models import Fix, Issue, Severity, ValidationResult
from prefact.rules import BaseRule, register


def _collect_imported_names(tree: ast.Module) -> dict[str, ast.stmt]:
    """Return {name: node} for every imported name at module level."""
    names: dict[str, ast.stmt] = {}
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                n = alias.asname or alias.name.split(".")[0]
                names[n] = node
        elif isinstance(node, ast.ImportFrom):
            if node.names and node.names[0].name == "*":
                continue
            for alias in node.names:
                n = alias.asname or alias.name
                names[n] = node
    return names


def _collect_used_names(tree: ast.Module) -> set[str]:
    """Return all Name.id values used outside import statements."""
    used: set[str] = set()
    import_lines = _get_import_lines(tree)
    
    for node in ast.walk(tree):
        # Handle direct name usage
        if isinstance(node, ast.Name) and getattr(node, "lineno", 0) not in import_lines:
            used.add(node.id)
        # Handle attribute chains (e.g., module.submodule.func)
        elif isinstance(node, ast.Attribute):
            root_name = _get_attribute_root(node)
            if root_name:
                used.add(root_name)
        # Handle __all__ exports
        elif isinstance(node, ast.Assign):
            _process_assignment_for_all(node, used)
    
    return used


def _get_import_lines(tree: ast.Module) -> set[int]:
    """Get line numbers of all import statements."""
    import_lines = set()
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            import_lines.add(node.lineno)
    return import_lines


def _get_attribute_root(node: ast.Attribute) -> Optional[str]:
    """Get the root name of an attribute chain."""
    root = node
    while isinstance(root, ast.Attribute):
        root = root.value
    if isinstance(root, ast.Name):
        return root.id
    return None


def _process_assignment_for_all(node: ast.Assign, used: set[str]) -> None:
    """Process assignment to __all__ and add exported names to used set."""
    for target in node.targets:
        if isinstance(target, ast.Name) and target.id == "__all__":
            if isinstance(node.value, (ast.List, ast.Tuple)):
                for elt in node.value.elts:
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        used.add(elt.value)


@register
class UnusedImports(BaseRule):
    rule_id = "unused-imports"
    description = "Detect imports that are never used in the module."

    def scan_file(self, path: Path, source: str) -> list[Issue]:
        issues: list[Issue] = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return issues

        imported = _collect_imported_names(tree)
        used = _collect_used_names(tree)

        for name, imp_node in imported.items():
            if name.startswith("_"):
                continue  # convention: _Foo may be re-exported
            if name not in used:
                issues.append(
                    Issue(
                        rule_id=self.rule_id,
                        file=path,
                        line=imp_node.lineno,
                        col=imp_node.col_offset,
                        message=f"Unused import: '{name}'",
                        severity=Severity.INFO,
                        original=name,
                    )
                )
        return issues

    def fix(self, path: Path, source: str, issues: list[Issue]) -> tuple[str, list[Fix]]:
        if not issues:
            return source, []

        unused_names = {i.original for i in issues}
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return source, []

        lines = source.splitlines(keepends=True)
        lines_to_remove: set[int] = set()
        fixes: list[Fix] = []

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ImportFrom):
                remaining = [a for a in node.names if (a.asname or a.name) not in unused_names]
                if not remaining:
                    for ln in range(node.lineno, (node.end_lineno or node.lineno) + 1):
                        lines_to_remove.add(ln)
                    fixes.append(
                        Fix(
                            issue=issues[0], file=path,
                            original_code=lines[node.lineno - 1].rstrip(),
                            fixed_code="", applied=True,
                        )
                    )
            elif isinstance(node, ast.Import):
                remaining = [
                    a for a in node.names if (a.asname or a.name.split(".")[0]) not in unused_names
                ]
                if not remaining:
                    for ln in range(node.lineno, (node.end_lineno or node.lineno) + 1):
                        lines_to_remove.add(ln)
                    fixes.append(
                        Fix(
                            issue=issues[0], file=path,
                            original_code=lines[node.lineno - 1].rstrip(),
                            fixed_code="", applied=True,
                        )
                    )

        new_lines = [l for i, l in enumerate(lines, 1) if i not in lines_to_remove]
        return "".join(new_lines), fixes

    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        checks, errors = [], []
        try:
            ast.parse(fixed)
            checks.append("syntax_valid")
        except SyntaxError as exc:
            errors.append(f"SyntaxError: {exc}")
        return ValidationResult(file=path, passed=not errors, checks=checks, errors=errors)
