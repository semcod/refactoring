"""Autoflake-based unused import and variable removal for pprefact.

This module provides integration with Autoflake for removing unused imports,
unused variables, and duplicate keys.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from prefact.config import Config
from prefact.models import Fix, Issue, Severity, ValidationResult
from prefact.rules import BaseRule, register


class AutoflakeHelper:
    """Helper class for Autoflake operations."""
    
    @staticmethod
    def check_file(file_path: Path, config: Optional[Dict] = None) -> List[Dict]:
        """Check a file for unused imports and variables using Autoflake."""
        # Autoflake doesn't have a check-only mode, so we simulate it
        # by running with --check-diff flag
        cmd = [
            "autoflake",
            "--check-diff",
            "--remove-unused-variables",
            "--remove-all-unused-imports",
            str(file_path)
        ]
        
        if config and config.get("ignore_init_module_imports"):
            cmd.append("--ignore-init-module-imports")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False  # Autoflake returns non-zero on changes
            )
            
            # Parse output to find issues
            issues = []
            if result.returncode != 0:
                lines = result.stdout.splitlines()
                for line in lines:
                    if line.startswith("-") and ("import" in line or "from" in line):
                        # This is a removed import
                        issues.append({
                            "type": "unused_import",
                            "line": line,
                            "message": "Unused import detected"
                        })
                    elif line.startswith("-") and "=" in line:
                        # This might be an unused variable
                        issues.append({
                            "type": "unused_variable",
                            "line": line,
                            "message": "Unused variable detected"
                        })
            
            return issues
        except (subprocess.SubprocessError, FileNotFoundError):
            return []
    
    @staticmethod
    def check_source(source: str, config: Optional[Dict] = None) -> List[Dict]:
        """Check source code for unused imports and variables."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
            tmp.write(source)
            tmp_path = tmp.name
        
        try:
            return AutoflakeHelper.check_file(Path(tmp_path), config)
        finally:
            import os
            os.unlink(tmp_path)
    
    @staticmethod
    def fix_file(file_path: Path, config: Optional[Dict] = None) -> bool:
        """Remove unused imports and variables from a file."""
        cmd = [
            "autoflake",
            "--in-place",
            "--remove-unused-variables",
            "--remove-all-unused-imports",
            str(file_path)
        ]
        
        if config:
            if config.get("ignore_init_module_imports"):
                cmd.append("--ignore-init-module-imports")
            if config.get("remove_duplicate_keys"):
                cmd.append("--remove-duplicate-keys")
            if config.get("remove_rhs_for_unused_variables"):
                cmd.append("--remove-rhs-for-unused-variables")
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    @staticmethod
    def fix_source(source: str, config: Optional[Dict] = None) -> str:
        """Remove unused imports and variables from source code."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
            tmp.write(source)
            tmp_path = tmp.name
        
        try:
            success = AutoflakeHelper.fix_file(Path(tmp_path), config)
            if success:
                with open(tmp_path, 'r') as f:
                    return f.read()
            return source
        finally:
            import os
            os.unlink(tmp_path)


@register
class AutoflakeUnusedImports(BaseRule):
    """Remove unused imports using Autoflake."""
    
    rule_id = "unused-imports"
    description = "Remove unused imports using Autoflake"
    
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.autoflake_config = self._load_autoflake_config()
    
    def _load_autoflake_config(self) -> Dict:
        """Load Autoflake configuration from prefact config."""
        return {
            "ignore_init_module_imports": self.config.get_rule_option(
                self.rule_id, "ignore_init_module_imports", True
            ),
            "remove_duplicate_keys": self.config.get_rule_option(
                self.rule_id, "remove_duplicate_keys", False
            ),
        }
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        issues = []
        results = AutoflakeHelper.check_source(source, self.autoflake_config)
        
        line_num = 1
        for item in results:
            if item["type"] == "unused_import":
                # Extract import name from the line
                import_name = self._extract_import_name(item["line"])
                
                issues.append(Issue(
                    rule_id=self.rule_id,
                    file=path,
                    line=line_num,
                    col=0,
                    message=f"Unused import: {import_name}",
                    severity=Severity.INFO,
                    original=import_name
                ))
            line_num += 1
        
        return issues
    
    def _extract_import_name(self, line: str) -> str:
        """Extract the import name from a diff line."""
        # Remove the leading "- " from diff output
        clean_line = line[2:] if line.startswith("- ") else line
        
        if "import " in clean_line:
            if clean_line.startswith("from "):
                # from x import y
                parts = clean_line.split()
                if len(parts) >= 4:
                    return parts[3]
            else:
                # import x
                parts = clean_line.split()
                if len(parts) >= 2:
                    return parts[1].split(",")[0]
        
        return "unknown"
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        if not issues:
            return source, []
        
        fixed_source = AutoflakeHelper.fix_source(source, self.autoflake_config)
        fixes = []
        
        if fixed_source != source:
            for issue in issues:
                fixes.append(Fix(
                    issue=issue,
                    file=path,
                    original_code=issue.original,
                    fixed_code="",
                    applied=True
                ))
        
        return fixed_source, fixes
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        # Check if unused imports remain
        remaining = AutoflakeHelper.check_source(fixed, self.autoflake_config)
        unused_imports = [r for r in remaining if r["type"] == "unused_import"]
        
        return ValidationResult(
            file=path,
            passed=len(unused_imports) == 0,
            checks=["no_unused_imports"] if not unused_imports else [],
            errors=[f"Still has {len(unused_imports)} unused imports"] if unused_imports else []
        )


@register
class AutoflakeUnusedVariables(BaseRule):
    """Remove unused variables using Autoflake."""
    
    rule_id = "unused-variables"
    description = "Remove unused variables using Autoflake"
    
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.autoflake_config = self._load_autoflake_config()
    
    def _load_autoflake_config(self) -> Dict:
        """Load Autoflake configuration."""
        return {
            "remove_rhs_for_unused_variables": self.config.get_rule_option(
                self.rule_id, "remove_rhs_for_unused_variables", False
            ),
        }
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        issues = []
        results = AutoflakeHelper.check_source(source, self.autoflake_config)
        
        line_num = 1
        for item in results:
            if item["type"] == "unused_variable":
                # Extract variable name from the line
                var_name = self._extract_variable_name(item["line"])
                
                issues.append(Issue(
                    rule_id=self.rule_id,
                    file=path,
                    line=line_num,
                    col=0,
                    message=f"Unused variable: {var_name}",
                    severity=Severity.INFO,
                    original=var_name
                ))
            line_num += 1
        
        return issues
    
    def _extract_variable_name(self, line: str) -> str:
        """Extract the variable name from a diff line."""
        # Remove the leading "- " from diff output
        clean_line = line[2:] if line.startswith("- ") else line
        
        if "=" in clean_line:
            var_name = clean_line.split("=")[0].strip()
            # Remove any type annotations
            if ":" in var_name:
                var_name = var_name.split(":")[0].strip()
            return var_name
        
        return "unknown"
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        if not issues:
            return source, []
        
        fixed_source = AutoflakeHelper.fix_source(source, self.autoflake_config)
        fixes = []
        
        if fixed_source != source:
            for issue in issues:
                fixes.append(Fix(
                    issue=issue,
                    file=path,
                    original_code=issue.original,
                    fixed_code="",
                    applied=True
                ))
        
        return fixed_source, fixes
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        # Check if unused variables remain
        remaining = AutoflakeHelper.check_source(fixed, self.autoflake_config)
        unused_vars = [r for r in remaining if r["type"] == "unused_variable"]
        
        return ValidationResult(
            file=path,
            passed=len(unused_vars) == 0,
            checks=["no_unused_variables"] if not unused_vars else [],
            errors=[f"Still has {len(unused_vars)} unused variables"] if unused_vars else []
        )


@register
class AutoflakeDuplicateKeys(BaseRule):
    """Remove duplicate keys in dictionaries using Autoflake."""
    
    rule_id = "duplicate-keys"
    description = "Remove duplicate keys in dictionaries"
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        # Autoflake handles this as part of its general cleanup
        # We'll use a simple AST-based detection for reporting
        import ast
        
        issues = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return issues
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                # Check for duplicate keys
                seen_keys = set()
                for key in node.keys:
                    if isinstance(key, ast.Constant) and isinstance(key.value, str):
                        if key.value in seen_keys:
                            issues.append(Issue(
                                rule_id=self.rule_id,
                                file=path,
                                line=node.lineno,
                                col=node.col_offset,
                                message=f"Duplicate key in dictionary: '{key.value}'",
                                severity=Severity.WARNING,
                                original=key.value
                            ))
                        seen_keys.add(key.value)
        
        return issues
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        if not issues:
            return source, []
        
        # Use Autoflake with --remove-duplicate-keys
        config = {"remove_duplicate_keys": True}
        fixed_source = AutoflakeHelper.fix_source(source, config)
        fixes = []
        
        if fixed_source != source:
            for issue in issues:
                fixes.append(Fix(
                    issue=issue,
                    file=path,
                    original_code=f"duplicate key: {issue.original}",
                    fixed_code="duplicate key removed",
                    applied=True
                ))
        
        return fixed_source, fixes
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        # Re-scan for duplicate keys
        issues = self.scan_file(path, fixed)
        
        return ValidationResult(
            file=path,
            passed=len(issues) == 0,
            checks=["no_duplicate_keys"] if not issues else [],
            errors=[f"Still has {len(issues)} duplicate keys"] if issues else []
        )


# Combined rule for all Autoflake features
@register
class AutoflakeAll(BaseRule):
    """Apply all Autoflake fixes: unused imports, variables, and duplicate keys."""
    
    rule_id = "autoflake-all"
    description = "Apply all Autoflake fixes"
    
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.autoflake_config = {
            "ignore_init_module_imports": config.get_rule_option(
                "unused-imports", "ignore_init_module_imports", True
            ),
            "remove_duplicate_keys": config.get_rule_option(
                "duplicate-keys", "enabled", False
            ),
            "remove_rhs_for_unused_variables": config.get_rule_option(
                "unused-variables", "remove_rhs_for_unused_variables", False
            ),
        }
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        # Combine all Autoflake checks
        all_issues = []
        
        # Check unused imports
        unused_rule = AutoflakeUnusedImports(self.config)
        all_issues.extend(unused_rule.scan_file(path, source))
        
        # Check unused variables
        var_rule = AutoflakeUnusedVariables(self.config)
        all_issues.extend(var_rule.scan_file(path, source))
        
        # Check duplicate keys
        dup_rule = AutoflakeDuplicateKeys(self.config)
        all_issues.extend(dup_rule.scan_file(path, source))
        
        return all_issues
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        if not issues:
            return source, []
        
        fixed_source = AutoflakeHelper.fix_source(source, self.autoflake_config)
        fixes = []
        
        if fixed_source != source:
            for issue in issues:
                fixes.append(Fix(
                    issue=issue,
                    file=path,
                    original_code=issue.original,
                    fixed_code="removed",
                    applied=True
                ))
        
        return fixed_source, fixes
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        # Run all validations
        all_checks = []
        all_errors = []
        
        # Check unused imports
        unused_rule = AutoflakeUnusedImports(self.config)
        result1 = unused_rule.validate(path, original, fixed)
        all_checks.extend(result1.checks)
        all_errors.extend(result1.errors)
        
        # Check unused variables
        var_rule = AutoflakeUnusedVariables(self.config)
        result2 = var_rule.validate(path, original, fixed)
        all_checks.extend(result2.checks)
        all_errors.extend(result2.errors)
        
        # Check duplicate keys
        dup_rule = AutoflakeDuplicateKeys(self.config)
        result3 = dup_rule.validate(path, original, fixed)
        all_checks.extend(result3.checks)
        all_errors.extend(result3.errors)
        
        return ValidationResult(
            file=path,
            passed=len(all_errors) == 0,
            checks=all_checks,
            errors=all_errors
        )
