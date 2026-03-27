"""Ruff-based rules - fast implementation for multiple rule types."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Dict, List

from prefact.config import Config
from prefact.models import Fix, Issue, Severity, ValidationResult
from prefact.rules import BaseRule, register


class RuffHelper:
    """Helper class for Ruff operations."""
    
    @staticmethod
    def check_file(file_path: Path, select_codes: List[str]) -> List[Dict]:
        """Run Ruff on a single file and return JSON results."""
        try:
            result = subprocess.run([
                "ruff", "check", str(file_path),
                "--select", ",".join(select_codes),
                "--output-format", "json",
                "--no-fix"
            ], capture_output=True, text=True, check=False)  # Use check=False to handle non-zero exit
            
            if result.stdout.strip():
                return json.loads(result.stdout)
            return []
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            return []
    
    @staticmethod
    def fix_file(file_path: Path, select_codes: List[str]) -> bool:
        """Run Ruff with --fix on a file."""
        try:
            subprocess.run([
                "ruff", "check", str(file_path),
                "--select", ",".join(select_codes),
                "--fix"
            ], check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    @staticmethod
    def fix_source(source: str, select_codes: List[str]) -> str:
        """Fix source code in memory using Ruff."""
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
            tmp.write(source)
            tmp_path = tmp.name
        
        try:
            success = RuffHelper.fix_file(Path(tmp_path), select_codes)
            if success:
                with open(tmp_path, 'r') as f:
                    return f.read()
            return source
        finally:
            import os
            os.unlink(tmp_path)


@register
class RuffWildcardImports(BaseRule):
    """Wildcard imports detection using Ruff."""
    
    rule_id = "wildcard-imports"
    description = "Detect wildcard imports (from x import *)"
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        issues = []
        results = RuffHelper.check_file(path, ["F403"])  # F403 = star-imports
        
        for item in results:
            issues.append(Issue(
                rule_id=self.rule_id,
                file=path,
                line=item["location"]["row"],
                col=item["location"]["column"],
                message=item["message"],
                severity=Severity.WARNING,
                original=item["message"]
            ))
        
        return issues
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        # Ruff doesn't auto-fix wildcard imports, so we just report
        return source, []
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        return ValidationResult(file=path, passed=True, checks=[], errors=[])


@register
class RuffPrintStatements(BaseRule):
    """Print statements detection using Ruff."""
    
    rule_id = "print-statements"
    description = "Detect print statements"
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        issues = []
        results = RuffHelper.check_file(path, ["T201"])  # T201 = print
        
        for item in results:
            # Check if file should be ignored
            if self._should_ignore_file(path):
                continue
                
            issues.append(Issue(
                rule_id=self.rule_id,
                file=path,
                line=item["location"]["row"],
                col=item["location"]["column"],
                message=item["message"],
                severity=Severity.INFO,
                original="print()"
            ))
        
        return issues
    
    def _should_ignore_file(self, path: Path) -> bool:
        """Check if file should be ignored based on config."""
        ignore_patterns = getattr(self.config, 'ignore_print_patterns', [])
        return any(pattern in str(path) for pattern in ignore_patterns)
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        if not issues:
            return source, []
        
        # Ruff can remove print statements
        success = RuffHelper.fix_file(path, ["T201"])
        fixes = []
        
        if success:
            fixed_source = path.read_text(encoding="utf-8")
            for issue in issues:
                fixes.append(Fix(
                    issue=issue,
                    file=path,
                    original_code="print(...)",
                    fixed_code="# Removed print statement",
                    applied=True
                ))
            return fixed_source, fixes
        
        return source, []
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        return ValidationResult(file=path, passed=True, checks=[], errors=[])


@register
class RuffUnusedImports(BaseRule):
    """Unused imports detection and removal using Ruff."""
    
    rule_id = "unused-imports"
    description = "Detect and remove unused imports"
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        issues = []
        results = RuffHelper.check_file(path, ["F401"])  # F401 = unused-import
        
        for item in results:
            # Extract import name from message
            message = item["message"]
            if "`" in message:
                import_name = message.split("`")[1]
                issues.append(Issue(
                    rule_id=self.rule_id,
                    file=path,
                    line=item["location"]["row"],
                    col=item["location"]["column"],
                    message=f"Unused import: {import_name}",
                    severity=Severity.INFO,
                    original=import_name
                ))
        
        return issues
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        if not issues:
            return source, []
        
        # Use Ruff to remove unused imports
        success = RuffHelper.fix_file(path, ["F401"])
        fixes = []
        
        if success:
            fixed_source = path.read_text(encoding="utf-8")
            for issue in issues:
                fixes.append(Fix(
                    issue=issue,
                    file=path,
                    original_code=issue.original,
                    fixed_code="",
                    applied=True
                ))
            return fixed_source, fixes
        
        return source, []
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        # Verify no unused imports remain
        remaining = RuffHelper.check_file(path, ["F401"])
        return ValidationResult(
            file=path,
            passed=len(remaining) == 0,
            checks=["no_unused_imports"] if not remaining else [],
            errors=[f"Still has unused imports: {len(remaining)}"] if remaining else []
        )


@register
class RuffSortedImports(BaseRule):
    """Import sorting using Ruff."""
    
    rule_id = "sorted-imports"
    description = "Sort imports according to PEP8"
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        issues = []
        results = RuffHelper.check_file(path, ["I001", "I002"])  # I001 = unsorted, I002 = missing newline
        
        for item in results:
            issues.append(Issue(
                rule_id=self.rule_id,
                file=path,
                line=item["location"]["row"],
                col=item["location"]["column"],
                message=item["message"],
                severity=Severity.INFO,
                original="unsorted imports"
            ))
        
        return issues
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        if not issues:
            return source, []
        
        # Use Ruff to sort imports
        success = RuffHelper.fix_file(path, ["I001", "I002"])
        fixes = []
        
        if success:
            fixed_source = path.read_text(encoding="utf-8")
            for issue in issues:
                fixes.append(Fix(
                    issue=issue,
                    file=path,
                    original_code="unsorted imports",
                    fixed_code="sorted imports",
                    applied=True
                ))
            return fixed_source, fixes
        
        return source, []
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        # Verify imports are sorted
        remaining = RuffHelper.check_file(path, ["I001", "I002"])
        return ValidationResult(
            file=path,
            passed=len(remaining) == 0,
            checks=["imports_sorted"] if not remaining else [],
            errors=["Imports not properly sorted"] if remaining else []
        )


@register
class RuffDuplicateImports(BaseRule):
    """Duplicate imports detection using Ruff."""
    
    rule_id = "duplicate-imports"
    description = "Detect duplicate imports"
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        issues = []
        # Ruff doesn't have a specific code for duplicate imports
        # We'll use F811 (redefined) which catches some cases
        results = RuffHelper.check_file(path, ["F811"])
        
        for item in results:
            if "redefined" in item["message"].lower() and "import" in item["message"].lower():
                issues.append(Issue(
                    rule_id=self.rule_id,
                    file=path,
                    line=item["location"]["row"],
                    col=item["location"]["column"],
                    message=item["message"],
                    severity=Severity.WARNING,
                    original="duplicate import"
                ))
        
        return issues
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        # Ruff doesn't auto-fix duplicate imports
        # Would need custom implementation
        return source, []
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        return ValidationResult(file=path, passed=True, checks=[], errors=[])
