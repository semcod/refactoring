"""MyPy-based type checking rules for prefact.

This module provides integration with MyPy for detecting type-related issues,
particularly missing return type annotations.
"""

import ast
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

import libcst as cst

from prefact.config import Config
from prefact.models import Fix, Issue, Severity, ValidationResult
from prefact.rules import BaseRule, register


class MyPyHelper:
    """Helper class for MyPy operations."""
    
    @staticmethod
    def check_file(file_path: Path, config: Optional[Dict] = None) -> List[Dict]:
        """Run MyPy on a single file and return JSON results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            report_file = Path(tmpdir) / "result.json"
            
            cmd = [
                "mypy", str(file_path),
                "--show-error-codes",
                "--no-error-summary",
                "--json-report", str(tmpdir),
                "--check-untyped-defs"
            ]
            
            # Add additional config options
            if config:
                if config.get("strict"):
                    cmd.append("--strict")
                if config.get("ignore_missing_imports"):
                    cmd.append("--ignore-missing-imports")
            
            try:
                subprocess.run(cmd, capture_output=True, check=True)
                
                # Read JSON report
                if report_file.exists():
                    with open(report_file) as f:
                        report = json.load(f)
                    
                    # Extract errors from report
                    errors = []
                    for file_data in report.get("files", []):
                        for msg in file_data.get("messages", []):
                            errors.append({
                                "file": file_data.get("path"),
                                "line": msg.get("line"),
                                "column": msg.get("column"),
                                "message": msg.get("message"),
                                "code": msg.get("code"),
                                "severity": msg.get("severity", "error")
                            })
                    return errors
            except subprocess.CalledProcessError:
                # MyPy returns non-zero exit code on type errors
                pass
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        
        return []
    
    @staticmethod
    def check_source(source: str, config: Optional[Dict] = None) -> List[Dict]:
        """Check source code in memory using MyPy."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
            tmp.write(source)
            tmp_path = tmp.name
        
        try:
            return MyPyHelper.check_file(Path(tmp_path), config)
        finally:
            import os
            os.unlink(tmp_path)


@register
class MyPyMissingReturnType(BaseRule):
    """Detect missing return type annotations using MyPy."""
    
    rule_id = "missing-return-type"
    description = "Detect functions missing return type annotations"
    
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.mypy_config = self._load_mypy_config()
    
    def _load_mypy_config(self) -> Dict:
        """Load MyPy configuration from prefact config."""
        return {
            "strict": self.config.get_rule_option(self.rule_id, "strict", False),
            "ignore_missing_imports": self.config.get_rule_option(
                self.rule_id, "ignore_missing_imports", True
            )
        }
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        issues = []
        results = MyPyHelper.check_file(path, self.mypy_config)
        
        for item in results:
            # Filter for missing return type errors
            if item.get("code") in ["no-return-type", "no-untyped-def"]:
                # Check if function is public (doesn't start with _)
                if self._is_public_function(path, item.get("line", 0)):
                    issues.append(Issue(
                        rule_id=self.rule_id,
                        file=path,
                        line=item.get("line", 0),
                        col=item.get("column", 0),
                        message=item.get("message", "Missing return type annotation"),
                        severity=Severity.INFO,
                        original="def function(...):"
                    ))
        
        return issues
    
    def _is_public_function(self, path: Path, line_num: int) -> bool:
        """Check if the function at line_num is public."""
        try:
            source = path.read_text(encoding="utf-8")
            lines = source.splitlines()
            if 0 < line_num <= len(lines):
                line = lines[line_num - 1]
                # Simple check: public functions don't start with underscore
                return "def _" not in line
        except Exception:
            pass
        return True
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        # MyPy doesn't auto-fix missing return types
        # Would need to infer types or add -> Any
        return source, []
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        # Check if missing return types were added
        remaining = MyPyHelper.check_file(path, self.mypy_config)
        missing_types = [
            r for r in remaining 
            if r.get("code") in ["no-return-type", "no-untyped-def"]
        ]
        
        return ValidationResult(
            file=path,
            passed=len(missing_types) == 0,
            checks=["return_types_annotated"] if not missing_types else [],
            errors=[f"Still missing {len(missing_types)} return types"] if missing_types else []
        )


@register
class MyPyTypeChecking(BaseRule):
    """General type checking using MyPy."""
    
    rule_id = "type-checking"
    description = "Run MyPy type checking on the code"
    
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.mypy_config = self._load_mypy_config()
    
    def _load_mypy_config(self) -> Dict:
        """Load MyPy configuration."""
        return {
            "strict": self.config.get_rule_option(self.rule_id, "strict", False),
            "ignore_missing_imports": self.config.get_rule_option(
                self.rule_id, "ignore_missing_imports", True
            )
        }
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        issues = []
        results = MyPyHelper.check_file(path, self.mypy_config)
        
        for item in results:
            # Map MyPy severity to prefact severity
            severity = (
                Severity.ERROR if item.get("severity") == "error" 
                else Severity.WARNING
            )
            
            issues.append(Issue(
                rule_id=self.rule_id,
                file=path,
                line=item.get("line", 0),
                col=item.get("column", 0),
                message=f"[{item.get('code', 'type')}] {item.get('message')}",
                severity=severity,
                original=item.get("code", "")
            ))
        
        return issues
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        # MyPy doesn't provide auto-fixes
        return source, []
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        # Run MyPy to check if type errors were resolved
        results = MyPyHelper.check_file(path, self.mypy_config)
        errors = [r for r in results if r.get("severity") == "error"]
        
        return ValidationResult(
            file=path,
            passed=len(errors) == 0,
            checks=["no_type_errors"] if not errors else [],
            errors=[f"{len(errors)} type errors remain"] if errors else []
        )


# Advanced: Type inference for automatic return type suggestions
class ReturnTypeInferrer:
    """Infer return types for simple functions."""
    
    @staticmethod
    def infer_return_type(source: str, func_name: str) -> Optional[str]:
        """Try to infer return type of a function."""
        
        try:
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == func_name:
                    return_types = ReturnTypeInferrer._analyze_return_types(node)
                    return ReturnTypeInferrer._unify_types(return_types)
        except SyntaxError:
            pass
        
        return None
    
    @staticmethod
    def _analyze_return_types(node: ast.FunctionDef) -> set[str]:
        """Analyze all return statements in a function."""
        return_types = set()
        
        for n in ast.walk(node):
            if isinstance(n, ast.Return):
                type_name = ReturnTypeInferrer._get_return_value_type(n.value)
                if type_name:
                    return_types.add(type_name)
        
        return return_types
    
    @staticmethod
    def _get_return_value_type(value: Optional[ast.expr]) -> str:
        """Get type name of a return value."""
        if value is None:
            return "None"
        
        # Type mapping for different AST node types
        type_map = {
            ast.Constant: lambda v: type(v.value).__name__,
            ast.NameConstant: lambda v: type(v.value).__name__,
            ast.List: lambda v: "List",
            ast.Dict: lambda v: "Dict",
        }
        
        for ast_type, type_func in type_map.items():
            if isinstance(value, ast_type):
                return type_func(value)
        
        return "Any"
    
    @staticmethod
    def _unify_types(return_types: set[str]) -> str:
        """Unify multiple return types into a single type annotation."""
        if not return_types:
            return "None"
        elif len(return_types) == 1:
            return return_types.pop()
        elif "None" in return_types and len(return_types) == 2:
            types_copy = return_types.copy()
            types_copy.discard("None")
            other = types_copy.pop()
            return f"Optional[{other}]"
        else:
            return "Any"


class ReturnTypeAdder(cst.CSTTransformer):
    """Transformer to add return type annotations to functions."""
    
    def __init__(self, issues: List[Issue], path: Path):
        self.issues_by_line = {i.line: i for i in issues}
        self.fixes = []
        self.path = path
    
    def leave_FunctionDef(
        self,
        original_node: cst.FunctionDef,
        updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        if original_node.name.value in self.issues_by_line:
            issue = self.issues_by_line[original_node.name.value]
            inferred = issue.meta.get("inferred_type", "Any")
            
            if inferred:
                # Add return type annotation
                new_returns = cst.Annotation(
                    annotation=cst.Name(inferred)
                )
                updated_node = updated_node.with_changes(
                    returns=new_returns
                )
                
                self.fixes.append(Fix(
                    issue=issue,
                    file=self.path,
                    original_code=f"def {original_node.name.value}(...):",
                    fixed_code=f"def {original_node.name.value}(...) -> {inferred}:",
                    applied=True
                ))
        
        return updated_node


# Example: Enhanced rule with type inference
@register
class SmartReturnTypeRule(BaseRule):
    """Smart return type detection with inference suggestions."""
    
    rule_id = "smart-return-type"
    description = "Detect missing return types and suggest inferred types"
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        
        issues = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return issues
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check if function has return type annotation
                if node.returns is None and not node.name.startswith("_"):
                    # Try to infer return type
                    inferred = ReturnTypeInferrer.infer_return_type(source, node.name)
                    
                    message = f"Function '{node.name}' missing return type"
                    if inferred:
                        message += f" (suggested: -> {inferred})"
                    
                    issues.append(Issue(
                        rule_id=self.rule_id,
                        file=path,
                        line=node.lineno,
                        col=node.col_offset,
                        message=message,
                        severity=Severity.INFO,
                        original=f"def {node.name}(...):",
                        suggested=f"def {node.name}(...) -> {inferred or 'Any'}:" if inferred else None,
                        meta={"inferred_type": inferred}
                    ))
        
        return issues
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        
        if not issues:
            return source, []
        
        # Use LibCST for safe transformation
        try:
            cst_tree = cst.parse_module(source)
            transformer = ReturnTypeAdder(issues, path)
            fixed_tree = cst_tree.visit(transformer)
            return fixed_tree.code, transformer.fixes
        except cst.ParserSyntaxError:
            return source, []
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        # Simple syntax check
        try:
            ast.parse(fixed)
            return ValidationResult(file=path, passed=True, checks=["syntax_valid"], errors=[])
        except SyntaxError as e:
            return ValidationResult(
                file=path, 
                passed=False, 
                checks=[], 
                errors=[f"Syntax error: {e}"]
            )
