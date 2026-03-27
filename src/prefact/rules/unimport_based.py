"""Unimport-based unused import detection and removal for pprefact.

This module provides integration with the unimport library for fast and accurate
unused import detection and removal.
"""

from __future__ import annotations

import ast
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from prefact.config import Config
from prefact.models import Fix, Issue, Severity, ValidationResult
from prefact.rules import BaseRule, register


class UnimportHelper:
    """Helper class for unimport operations."""
    
    @staticmethod
    def check_file(file_path: Path, config: Optional[Dict] = None) -> List[Dict]:
        """Check a file for unused imports using unimport."""
        cmd = ["unimport", "--check", str(file_path)]
        
        if config:
            if config.get("include_star_import"):
                cmd.append("--include-star-import")
            if config.get("remove_duplicate_imports"):
                cmd.append("--remove-duplicate-imports")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            # Parse output to find unused imports
            issues = []
            if result.returncode != 0:  # unimport returns non-zero when issues found
                lines = result.stdout.splitlines()
                for line in lines:
                    if "unused import" in line.lower():
                        # Extract import name from line
                        import_name = UnimportHelper._extract_import_name(line)
                        if import_name:
                            issues.append({
                                "type": "unused_import",
                                "import": import_name,
                                "line": line
                            })
            
            return issues
        except (subprocess.SubprocessError, FileNotFoundError):
            return []
    
    @staticmethod
    def check_source(source: str, config: Optional[Dict] = None) -> List[Dict]:
        """Check source code for unused imports."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
            tmp.write(source)
            tmp_path = tmp.name
        
        try:
            return UnimportHelper.check_file(Path(tmp_path), config)
        finally:
            import os
            os.unlink(tmp_path)
    
    @staticmethod
    def _extract_import_name(line: str) -> Optional[str]:
        """Extract import name from unimport output."""
        # Example output: "unused import 'os' found"
        if "'" in line:
            parts = line.split("'")
            if len(parts) >= 3:
                return parts[1]
        return None
    
    @staticmethod
    def fix_file(file_path: Path, config: Optional[Dict] = None) -> bool:
        """Remove unused imports from a file using unimport."""
        cmd = ["unimport", "--remove", str(file_path)]
        
        if config:
            if config.get("include_star_import"):
                cmd.append("--include-star-import")
            if config.get("remove_duplicate_imports"):
                cmd.append("--remove-duplicate-imports")
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    @staticmethod
    def fix_source(source: str, config: Optional[Dict] = None) -> str:
        """Remove unused imports from source code."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
            tmp.write(source)
            tmp_path = tmp.name
        
        try:
            success = UnimportHelper.fix_file(Path(tmp_path), config)
            if success:
                with open(tmp_path, 'r') as f:
                    return f.read()
            return source
        finally:
            import os
            os.unlink(tmp_path)


@register
class UnimportUnusedImports(BaseRule):
    """Remove unused imports using unimport."""
    
    rule_id = "unused-imports"
    description = "Remove unused imports using unimport library"
    
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.unimport_config = self._load_unimport_config()
    
    def _load_unimport_config(self) -> Dict:
        """Load unimport configuration."""
        return {
            "include_star_import": self.config.get_rule_option(
                self.rule_id, "include_star_import", False
            ),
            "remove_duplicate_imports": self.config.get_rule_option(
                self.rule_id, "remove_duplicate_imports", True
            ),
            "diff": self.config.get_rule_option(
                self.rule_id, "diff", False
            )
        }
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        issues = []
        results = UnimportHelper.check_source(source, self.unimport_config)
        
        # Extract line numbers by parsing the source
        lines = source.splitlines()
        import_lines = {}
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                # Extract import names
                if stripped.startswith("from "):
                    parts = stripped.split()
                    if len(parts) >= 4:
                        import_name = parts[3]
                        import_lines[import_name] = i + 1
                else:
                    parts = stripped.split()
                    if len(parts) >= 2:
                        import_name = parts[1].split(",")[0]
                        import_lines[import_name] = i + 1
        
        for item in results:
            import_name = item.get("import", "unknown")
            line_num = import_lines.get(import_name, 1)
            
            issues.append(Issue(
                rule_id=self.rule_id,
                file=path,
                line=line_num,
                col=0,
                message=f"Unused import: {import_name}",
                severity=Severity.INFO,
                original=import_name
            ))
        
        return issues
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        if not issues:
            return source, []
        
        fixed_source = UnimportHelper.fix_source(source, self.unimport_config)
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
        remaining = UnimportHelper.check_source(fixed, self.unimport_config)
        
        return ValidationResult(
            file=path,
            passed=len(remaining) == 0,
            checks=["no_unused_imports"] if not remaining else [],
            errors=[f"Still has {len(remaining)} unused imports"] if remaining else []
        )


@register
class UnimportDuplicateImports(BaseRule):
    """Remove duplicate imports using unimport."""
    
    rule_id = "duplicate-imports"
    description = "Remove duplicate imports using unimport library"
    
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.unimport_config = {
            "remove_duplicate_imports": True
        }
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        # unimport handles duplicate imports as part of its main functionality
        # We'll use AST-based detection for reporting
        issues = []
        
        try:
            tree = ast.parse(source)
            imports = {}
            
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        name = alias.asname or alias.name
                        if name in imports:
                            issues.append(Issue(
                                rule_id=self.rule_id,
                                file=path,
                                line=node.lineno,
                                col=node.col_offset,
                                message=f"Duplicate import: {name}",
                                severity=Severity.WARNING,
                                original=name
                            ))
                        else:
                            imports[name] = node.lineno
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        name = alias.asname or alias.name
                        full_name = f"{module}.{name}" if module else name
                        if name in imports and imports[name] != node.lineno:
                            issues.append(Issue(
                                rule_id=self.rule_id,
                                file=path,
                                line=node.lineno,
                                col=node.col_offset,
                                message=f"Duplicate import: {full_name}",
                                severity=Severity.WARNING,
                                original=full_name
                            ))
                        else:
                            imports[name] = node.lineno
        except SyntaxError:
            pass
        
        return issues
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        if not issues:
            return source, []
        
        fixed_source = UnimportHelper.fix_source(source, self.unimport_config)
        fixes = []
        
        if fixed_source != source:
            for issue in issues:
                fixes.append(Fix(
                    issue=issue,
                    file=path,
                    original_code=issue.original,
                    fixed_code="duplicate removed",
                    applied=True
                ))
        
        return fixed_source, fixes
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        # Re-scan for duplicate imports
        issues = self.scan_file(path, fixed)
        
        return ValidationResult(
            file=path,
            passed=len(issues) == 0,
            checks=["no_duplicate_imports"] if not issues else [],
            errors=[f"Still has {len(issues)} duplicate imports"] if issues else []
        )


# Advanced: Unimport with star import handling
@register
class UnimportStarImports(BaseRule):
    """Handle star imports using unimport."""
    
    rule_id = "wildcard-imports"
    description = "Handle star imports using unimport library"
    
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.unimport_config = {
            "include_star_import": True
        }
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        issues = []
        
        # Find star imports
        try:
            tree = ast.parse(source)
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.ImportFrom):
                    if any(alias.name == "*" for alias in node.names):
                        module = node.module or ""
                        issues.append(Issue(
                            rule_id=self.rule_id,
                            file=path,
                            line=node.lineno,
                            col=node.col_offset,
                            message=f"Star import from {module}",
                            severity=Severity.WARNING,
                            original=f"from {module} import *"
                        ))
        except SyntaxError:
            pass
        
        return issues
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        # unimport can expand star imports if configured
        fixed_source = UnimportHelper.fix_source(source, self.unimport_config)
        fixes = []
        
        if fixed_source != source:
            for issue in issues:
                fixes.append(Fix(
                    issue=issue,
                    file=path,
                    original_code=issue.original,
                    fixed_code="expanded imports",
                    applied=True
                ))
        
        return fixed_source, fixes
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        # Check if star imports remain
        issues = self.scan_file(path, fixed)
        
        return ValidationResult(
            file=path,
            passed=len(issues) == 0,
            checks=["no_star_imports"] if not issues else [],
            errors=[f"Still has {len(issues)} star imports"] if issues else []
        )


# Combined unimport rule
@register
class UnimportAll(BaseRule):
    """Apply all unimport fixes."""
    
    rule_id = "unimport-all"
    description = "Apply all unimport fixes (unused, duplicate, star imports)"
    
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.unimport_config = {
            "include_star_import": config.get_rule_option(
                "wildcard-imports", "include_star_import", False
            ),
            "remove_duplicate_imports": True
        }
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        # Combine all unimport-based checks
        all_issues = []
        
        # Check unused imports
        unused_rule = UnimportUnusedImports(self.config)
        all_issues.extend(unused_rule.scan_file(path, source))
        
        # Check duplicate imports
        duplicate_rule = UnimportDuplicateImports(self.config)
        all_issues.extend(duplicate_rule.scan_file(path, source))
        
        # Check star imports
        star_rule = UnimportStarImports(self.config)
        all_issues.extend(star_rule.scan_file(path, source))
        
        return all_issues
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        if not issues:
            return source, []
        
        fixed_source = UnimportHelper.fix_source(source, self.unimport_config)
        fixes = []
        
        if fixed_source != source:
            for issue in issues:
                fixes.append(Fix(
                    issue=issue,
                    file=path,
                    original_code=issue.original,
                    fixed_code="fixed",
                    applied=True
                ))
        
        return fixed_source, fixes
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        # Run all validations
        all_checks = []
        all_errors = []
        
        # Check unused imports
        unused_rule = UnimportUnusedImports(self.config)
        result1 = unused_rule.validate(path, original, fixed)
        all_checks.extend(result1.checks)
        all_errors.extend(result1.errors)
        
        # Check duplicate imports
        duplicate_rule = UnimportDuplicateImports(self.config)
        result2 = duplicate_rule.validate(path, original, fixed)
        all_checks.extend(result2.checks)
        all_errors.extend(result2.errors)
        
        # Check star imports
        star_rule = UnimportStarImports(self.config)
        result3 = star_rule.validate(path, original, fixed)
        all_checks.extend(result3.checks)
        all_errors.extend(result3.errors)
        
        return ValidationResult(
            file=path,
            passed=len(all_errors) == 0,
            checks=all_checks,
            errors=all_errors
        )
