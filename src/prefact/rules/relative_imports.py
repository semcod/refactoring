"""Rule: convert relative (dotted) imports to absolute package imports.

Detects patterns like:
    from ....llm.generator import generate_strategy
and converts them to:
    from planfile.llm.generator import generate_strategy

Uses libcst for syntax-safe, formatting-preserving transformations.
"""

from __future__ import annotations

import ast
from pathlib import Path

import libcst as cst

from prefact.config import Config
from prefact.models import Fix, Issue, Severity, ValidationResult
from prefact.rules import BaseRule, register


# ── CST helpers ───────────────────────────────────────────────────────


def _module_to_str(node: cst.BaseExpression | None) -> str:
    """Convert a CST module node (Name | Attribute chain) to dotted string."""
    if node is None:
        return ""
    if isinstance(node, cst.Name):
        return node.value
    if isinstance(node, cst.Attribute):
        return f"{_module_to_str(node.value)}.{node.attr.value}"
    return ""


def _str_to_module(dotted: str) -> cst.BaseExpression:
    """Convert ``'a.b.c'`` to a CST Attribute chain."""
    parts = dotted.split(".")
    node: cst.BaseExpression = cst.Name(parts[0])
    for part in parts[1:]:
        node = cst.Attribute(value=node, attr=cst.Name(part))
    return node


class _RelativeImportFixer(cst.CSTTransformer):
    """Transform relative imports to absolute using the resolved package root."""

    def __init__(self, file_path: Path, package_name: str, project_root: Path) -> None:
        self.file_path = file_path
        self.package_name = package_name
        self.project_root = project_root
        self.fixes: list[dict] = []

    def leave_ImportFrom(
        self,
        original_node: cst.ImportFrom,
        updated_node: cst.ImportFrom,
    ) -> cst.ImportFrom:
        if not isinstance(updated_node.relative, (list, tuple)):
            return updated_node
        level = len(updated_node.relative) if isinstance(updated_node.relative, (list, tuple)) else 0
        if level == 0:
            return updated_node

        abs_module = self._resolve(level, updated_node.module)
        if abs_module is None:
            return updated_node

        new_module = _str_to_module(abs_module)
        self.fixes.append(
            {
                "original": "." * level + (_module_to_str(updated_node.module) if updated_node.module else ""),
                "fixed": abs_module,
            }
        )
        return updated_node.with_changes(relative=(), module=new_module)

    def _resolve(self, level: int, module_node: cst.BaseExpression | None) -> str | None:
        """Resolve ``level`` dots + ``module_node`` to an absolute dotted path."""
        try:
            rel = self.file_path.resolve().relative_to(self.project_root.resolve())
        except ValueError:
            return None

        parts = list(rel.parts)
        if parts and parts[0] == "src":
            parts = parts[1:]
        parts = parts[:-1]  # remove filename

        up = level - 1
        if up > len(parts):
            return None
        base_parts = parts[: len(parts) - up] if up else parts

        module_str = _module_to_str(module_node) if module_node else ""
        result_parts = list(base_parts) + ([module_str] if module_str else [])
        return ".".join(result_parts) if result_parts else None


# ── Rule ──────────────────────────────────────────────────────────────


@register
class RelativeToAbsoluteImports(BaseRule):
    rule_id = "relative-imports"
    description = "Convert relative (dotted) imports to absolute package imports."

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.package_name = config.detect_package_name()

    def scan_file(self, path: Path, source: str) -> list[Issue]:
        issues: list[Issue] = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return issues

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.level or 0) > 0:
                module_str = node.module or ""
                original = "." * node.level + module_str
                issues.append(
                    Issue(
                        rule_id=self.rule_id,
                        file=path,
                        line=node.lineno,
                        col=node.col_offset,
                        message=f"Relative import (level={node.level}): '{original}'",
                        severity=Severity.WARNING,
                        original=f"from {original} import ...",
                        suggested=f"from {self.package_name}.{module_str} import ..."
                        if self.package_name
                        else "",
                        meta={"level": node.level, "module": module_str},
                    )
                )
        return issues

    def fix(self, path: Path, source: str, issues: list[Issue]) -> tuple[str, list[Fix]]:
        if not issues or not self.package_name:
            return source, []

        try:
            cst_tree = cst.parse_module(source)
        except cst.ParserSyntaxError:
            return source, []

        transformer = _RelativeImportFixer(path, self.package_name, self.config.project_root)
        new_tree = cst_tree.visit(transformer)
        fixed_source = new_tree.code

        fixes = []
        for info in transformer.fixes:
            fixes.append(
                Fix(
                    issue=Issue(
                        rule_id=self.rule_id,
                        file=path,
                        line=0,
                        col=0,
                        message=f"Fixed: {info['original']} → {info['fixed']}",
                        original=info["original"],
                        suggested=info["fixed"],
                    ),
                    file=path,
                    original_code=info["original"],
                    fixed_code=info["fixed"],
                    applied=True,
                )
            )
        return fixed_source, fixes

    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        checks: list[str] = []
        errors: list[str] = []

        # 1. Syntax check
        try:
            ast.parse(fixed)
            checks.append("syntax_valid")
        except SyntaxError as exc:
            errors.append(f"SyntaxError after fix: {exc}")

        # 2. No remaining relative imports
        try:
            tree = ast.parse(fixed)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and (node.level or 0) > 0:
                    errors.append(
                        f"Line {node.lineno}: still has relative import (level={node.level})"
                    )
            if not errors:
                checks.append("no_relative_imports")
        except SyntaxError:
            pass

        # 3. Import count preserved
        try:
            orig_count = sum(
                1 for n in ast.walk(ast.parse(original)) if isinstance(n, (ast.Import, ast.ImportFrom))
            )
            fix_count = sum(
                1 for n in ast.walk(ast.parse(fixed)) if isinstance(n, (ast.Import, ast.ImportFrom))
            )
            if orig_count == fix_count:
                checks.append("import_count_preserved")
            else:
                errors.append(f"Import count changed: {orig_count} → {fix_count}")
        except SyntaxError:
            pass

        return ValidationResult(file=path, passed=len(errors) == 0, checks=checks, errors=errors)
