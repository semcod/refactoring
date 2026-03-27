"""LibCST-based string concatenation to f-string transformations.

This module provides rules for converting string concatenations to f-strings
using LibCST for safe, formatting-preserving transformations.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import List, Optional

import libcst as cst
from libcst import matchers as m

from prefact.config import Config
from prefact.models import Fix, Issue, Severity, ValidationResult
from prefact.rules import BaseRule, register


class StringConcatTransformer(cst.CSTTransformer):
    """Transform string concatenations to f-strings."""
    
    def __init__(self):
        self.fixes = []
        self.changes = []
    
    def leave_BinaryOperation(
        self,
        original_node: cst.BinaryOperation,
        updated_node: cst.BinaryOperation,
    ) -> cst.CSTNode:
        # Check if this is a string concatenation
        if not isinstance(updated_node.operator, cst.Add):
            return updated_node
        
        # Collect all string parts
        parts = self._collect_string_parts(updated_node)
        
        if parts and self._should_transform(parts):
            # Create f-string
            fstring = self._create_fstring(parts)
            if fstring:
                self.fixes.append({
                    "line": original_node.position.start.line if original_node.position else 0,
                    "original": cst.Module([]).code_for_node(original_node),
                    "fixed": cst.Module([]).code_for_node(fstring)
                })
                return fstring
        
        return updated_node
    
    def _collect_string_parts(self, node: cst.BinaryOperation) -> List[dict]:
        """Recursively collect all parts of a string concatenation."""
        parts = []
        
        def collect(n):
            if isinstance(n, cst.BinaryOperation) and isinstance(n.operator, cst.Add):
                collect(n.left)
                collect(n.right)
            elif isinstance(n, cst.SimpleString):
                # Evaluate the string value
                value = self._eval_string(n)
                if value is not None:
                    parts.append({"type": "string", "value": value, "node": n})
            else:
                # This is a variable or expression
                parts.append({"type": "expr", "node": n})
        
        collect(node)
        return parts
    
    def _eval_string(self, node: cst.SimpleString) -> Optional[str]:
        """Evaluate a string literal node."""
        try:
            # Get the raw value
            raw = node.value
            if raw.startswith(("'", '"')):
                # Single or double quotes
                return ast.literal_eval(raw)
            elif raw.startswith(("'''", '"""')):
                # Triple quotes
                return ast.literal_eval(raw)
            elif raw.startswith(('r"', "r'", 'r"""', "r'''")):
                # Raw string
                return ast.literal_eval(raw[1:])
        except Exception:
            pass
        return None
    
    def _should_transform(self, parts: List[dict]) -> bool:
        """Check if we should transform this concatenation."""
        # Don't transform if:
        # - Only one part (no concatenation)
        # - Contains bytes literals
        # - Spans multiple lines with different quote types
        
        if len(parts) <= 1:
            return False
        
        # Check for bytes literals
        for part in parts:
            if isinstance(part["node"], cst.SimpleString):
                if part["node"].value.startswith(('b"', "b'")):
                    return False
        
        return True
    
    def _create_fstring(self, parts: List[dict]) -> Optional[cst.FormattedString]:
        """Create an f-string from parts."""
        # Build the f-string content
        content_parts = []
        
        for part in parts:
            if part["type"] == "string":
                # Add string content
                content_parts.append(
                    cst.FormattedStringText(
                        value=part["value"]
                    )
                )
            else:
                # Add expression
                content_parts.append(
                    cst.FormattedStringExpression(
                        expression=part["node"],
                        conversion=None,
                        format_spec=None
                    )
                )
        
        if content_parts:
            return cst.FormattedString(
                parts=content_parts,
                start='f"',
                end='"'
            )
        
        return None


@register
class StringConcatToFString(BaseRule):
    """Convert string concatenations to f-strings."""
    
    rule_id = "string-concat"
    description = "Convert string concatenations to f-strings"
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        issues = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return issues
        
        # Find string concatenations
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                if self._is_string_concat(node):
                    issues.append(Issue(
                        rule_id=self.rule_id,
                        file=path,
                        line=node.lineno,
                        col=node.col_offset,
                        message="String concatenation can be converted to f-string",
                        severity=Severity.INFO,
                        original="string concatenation"
                    ))
        
        return issues
    
    def _is_string_concat(self, node: ast.BinOp) -> bool:
        """Check if a BinOp is a string concatenation."""
        def check(n):
            if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
                return check(n.left) and check(n.right)
            elif isinstance(n, ast.Str) or isinstance(n, ast.Constant) and isinstance(n.value, str):
                return True
            else:
                # Allow variables/expressions in the mix
                return True
        
        return check(node.left) and check(node.right)
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        if not issues:
            return source, []
        
        try:
            cst_tree = cst.parse_module(source)
        except cst.ParserSyntaxError:
            return source, []
        
        transformer = StringConcatTransformer()
        fixed_tree = cst_tree.visit(transformer)
        fixed_source = fixed_tree.code
        
        fixes = []
        for fix_info in transformer.fixes:
            fixes.append(Fix(
                issue=Issue(
                    rule_id=self.rule_id,
                    file=path,
                    line=fix_info["line"],
                    col=0,
                    message="Converted string concatenation to f-string",
                    original=fix_info["original"],
                    suggested=fix_info["fixed"]
                ),
                file=path,
                original_code=fix_info["original"],
                fixed_code=fix_info["fixed"],
                applied=True
            ))
        
        return fixed_source, fixes
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        checks = []
        errors = []
        
        # Check syntax
        try:
            ast.parse(fixed)
            checks.append("syntax_valid")
        except SyntaxError as e:
            errors.append(f"Syntax error: {e}")
        
        # Check if string concatenations remain
        try:
            tree = ast.parse(fixed)
            remaining_concats = 0
            for node in ast.walk(tree):
                if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                    if self._is_string_concat(node):
                        remaining_concats += 1
            
            if remaining_concats == 0:
                checks.append("no_string_concats")
            else:
                errors.append(f"Still has {remaining_concats} string concatenations")
        except SyntaxError:
            pass
        
        return ValidationResult(
            file=path,
            passed=len(errors) == 0,
            checks=checks,
            errors=errors
        )


# Alternative: Using flynt library for more robust transformations
class FlyntHelper:
    """Helper for using flynt library for string formatting."""
    
    @staticmethod
    def fix_source(source: str) -> str:
        """Use flynt to fix string formatting."""
        try:
            import flynt
            from flynt.api import api
            
            # Configure flynt
            options = {
                "aggressive": True,
                "multiline": True,
                "len_limit": 88,
            }
            
            # Apply transformations
            result = api.fstringify(source, **options)
            return result
        except ImportError:
            # flynt not available
            return source
        except Exception:
            # Error during transformation
            return source


@register
class FlyntStringFormatting(BaseRule):
    """Use flynt library for string formatting optimizations."""
    
    rule_id = "string-formatting"
    description = "Optimize string formatting using flynt"
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        # For simplicity, we'll just scan for common patterns
        # that flynt can optimize
        issues = []
        
        # Look for .format() calls
        if ".format(" in source:
            issues.append(Issue(
                rule_id=self.rule_id,
                file=path,
                line=1,
                col=0,
                message="String .format() calls can be converted to f-strings",
                severity=Severity.INFO,
                original=".format()"
            ))
        
        # Look for % formatting
        if "%" in source and ("'" in source or '"' in source):
            issues.append(Issue(
                rule_id=self.rule_id,
                file=path,
                line=1,
                col=0,
                message="Old-style string formatting can be converted to f-strings",
                severity=Severity.INFO,
                original="% formatting"
            ))
        
        return issues
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        if not issues:
            return source, []
        
        fixed_source = FlyntHelper.fix_source(source)
        fixes = []
        
        if fixed_source != source:
            for issue in issues:
                fixes.append(Fix(
                    issue=issue,
                    file=path,
                    original_code=issue.original,
                    fixed_code="f-string",
                    applied=True
                ))
        
        return fixed_source, fixes
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        # Simple validation - just check syntax
        try:
            ast.parse(fixed)
            return ValidationResult(
                file=path,
                passed=True,
                checks=["syntax_valid"],
                errors=[]
            )
        except SyntaxError as e:
            return ValidationResult(
                file=path,
                passed=False,
                checks=[],
                errors=[f"Syntax error: {e}"]
            )


# Advanced: Context-aware string transformation
class ContextAwareStringTransformer(cst.CSTTransformer):
    """Transform string concatenations with context awareness."""
    
    def __init__(self, config: Config):
        self.config = config
        self.fixes = []
        self.in_function_def = False
        self.in_class_def = False
        self.current_function = None
    
    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        self.in_function_def = True
        self.current_function = node.name.value
        return True
    
    def leave_FunctionDef(self, original_node: cst.FunctionDef) -> None:
        self.in_function_def = False
        self.current_function = None
    
    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        self.in_class_def = True
        return True
    
    def leave_ClassDef(self, original_node: cst.ClassDef) -> None:
        self.in_class_def = False
    
    def leave_BinaryOperation(
        self,
        original_node: cst.BinaryOperation,
        updated_node: cst.BinaryOperation,
    ) -> cst.CSTNode:
        # Skip if not string concatenation
        if not isinstance(updated_node.operator, cst.Add):
            return updated_node
        
        # Apply context-specific rules
        if self._should_skip_context(original_node):
            return updated_node
        
        # Use the same transformation logic as StringConcatTransformer
        transformer = StringConcatTransformer()
        result = transformer.leave_BinaryOperation(original_node, updated_node)
        
        if result != updated_node:
            self.fixes.extend(transformer.fixes)
        
        return result
    
    def _should_skip_context(self, node: cst.BinaryOperation) -> bool:
        """Check if we should skip transformation based on context."""
        # Skip in __repr__ methods (often use concatenation)
        if self.current_function == "__repr__":
            return True
        
        # Skip in logging statements
        if self._is_in_logging_statement(node):
            return True
        
        # Skip if configured to skip
        if self.config.get_rule_option("string-concat", "skip_in_tests", False):
            # Check if in test file
            # (implementation depends on your project structure)
            pass
        
        return False
    
    def _is_in_logging_statement(self, node: cst.BinaryOperation) -> bool:
        """Check if this concatenation is part of a logging statement."""
        # This would need to walk up the AST to check
        # Simplified implementation
        return False


@register
class ContextAwareStringConcat(BaseRule):
    """Context-aware string concatenation to f-string conversion."""
    
    rule_id = "context-aware-string-concat"
    description = "Convert string concatenations to f-strings with context awareness"
    
    def __init__(self, config: Config) -> None:
        super().__init__(config)
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        # Use the basic scanner for now
        # Context awareness is applied during fixing
        return StringConcatToFString(self.config).scan_file(path, source)
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        if not issues:
            return source, []
        
        try:
            cst_tree = cst.parse_module(source)
        except cst.ParserSyntaxError:
            return source, []
        
        transformer = ContextAwareStringTransformer(self.config)
        fixed_tree = cst_tree.visit(transformer)
        fixed_source = fixed_tree.code
        
        fixes = []
        for fix_info in transformer.fixes:
            fixes.append(Fix(
                issue=Issue(
                    rule_id=self.rule_id,
                    file=path,
                    line=fix_info["line"],
                    col=0,
                    message="Converted string concatenation to f-string",
                    original=fix_info["original"],
                    suggested=fix_info["fixed"]
                ),
                file=path,
                original_code=fix_info["original"],
                fixed_code=fix_info["fixed"],
                applied=True
            ))
        
        return fixed_source, fixes
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        return StringConcatToFString(self.config).validate(path, original, fixed)
