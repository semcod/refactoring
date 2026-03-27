"""Pylint-based rules for prefact integration.

This module provides integration with Pylint for advanced static analysis,
including custom checkers for print statements and string concatenations.
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from prefact.config import Config
from prefact.models import Fix, Issue, Severity, ValidationResult
from prefact.rules import BaseRule, register


class PylintHelper:
    """Helper class for Pylint operations."""
    
    @staticmethod
    def check_file(file_path: Path, config: Optional[Dict] = None) -> List[Dict]:
        """Run Pylint on a file and return parsed results."""
        # Default Pylint configuration for prefact
        cmd = [
            "pylint",
            "--output-format=json",
            "--disable=all",
            "--enable=print-statement,consider-using-f-string",
            str(file_path)
        ]
        
        # Add custom configuration
        if config:
            if config.get("disable_codes"):
                cmd.append(f"--disable={config['disable_codes']}")
            if config.get("enable_codes"):
                cmd.append(f"--enable={config['enable_codes']}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False  # Pylint returns non-zero on issues
            )
            
            # Parse JSON output
            if result.stdout.strip():
                return json.loads(result.stdout)
            return []
        except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError):
            return []
    
    @staticmethod
    def check_source(source: str, config: Optional[Dict] = None) -> List[Dict]:
        """Check source code using Pylint."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
            tmp.write(source)
            tmp_path = tmp.name
        
        try:
            return PylintHelper.check_file(Path(tmp_path), config)
        finally:
            import os
            os.unlink(tmp_path)
    
    @staticmethod
    def fix_file(file_path: Path, fixes: List[str]) -> bool:
        """Apply Pylint-suggested fixes (limited support)."""
        # Pylint doesn't have built-in fixing capability
        # This would need to be implemented based on the suggestions
        return False


@register
class PylintPrintStatements(BaseRule):
    """Detect print statements using Pylint."""
    
    rule_id = "print-statements"
    description = "Detect print statements using Pylint"
    
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.pylint_config = self._load_pylint_config()
    
    def _load_pylint_config(self) -> Dict:
        """Load Pylint configuration."""
        return {
            "disable_codes": self.config.get_rule_option(
                self.rule_id, "disable_codes", ""
            ),
            "ignore_patterns": self.config.get_rule_option(
                self.rule_id, "ignore_patterns", []
            )
        }
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        issues = []
        
        # Check if file should be ignored
        if any(pattern in str(path) for pattern in self.pylint_config["ignore_patterns"]):
            return issues
        
        results = PylintHelper.check_source(source, self.pylint_config)
        
        for item in results:
            if item.get("message-id") == "W1201" or "print-statement" in item.get("message", "").lower():
                issues.append(Issue(
                    rule_id=self.rule_id,
                    file=path,
                    line=item.get("line", 0),
                    col=item.get("column", 0),
                    message=item.get("message", "Print statement found"),
                    severity=Severity.INFO,
                    original="print()"
                ))
        
        return issues
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        # Pylint doesn't fix, but we can implement simple print removal
        if not issues:
            return source, []
        
        # Simple transformation: comment out print statements
        lines = source.splitlines()
        fixes = []
        
        for issue in issues:
            line_idx = issue.line - 1
            if 0 <= line_idx < len(lines):
                line = lines[line_idx]
                if "print(" in line and not line.strip().startswith("#"):
                    lines[line_idx] = f"# {line}"
                    fixes.append(Fix(
                        issue=issue,
                        file=path,
                        original_code=line,
                        fixed_code=f"# {line}",
                        applied=True
                    ))
        
        return "\n".join(lines), fixes
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        # Check if print statements remain
        results = PylintHelper.check_source(fixed, self.pylint_config)
        remaining = [
            r for r in results 
            if r.get("message-id") == "W1201" or "print-statement" in r.get("message", "").lower()
        ]
        
        return ValidationResult(
            file=path,
            passed=len(remaining) == 0,
            checks=["no_print_statements"] if not remaining else [],
            errors=[f"Still has {len(remaining)} print statements"] if remaining else []
        )


@register
class PylintStringConcat(BaseRule):
    """Detect string concatenation using Pylint."""
    
    rule_id = "string-concat"
    description = "Detect string concatenation that should use f-strings"
    
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.pylint_config = self._load_pylint_config()
    
    def _load_pylint_config(self) -> Dict:
        """Load Pylint configuration."""
        return {
            "enable_codes": "consider-using-f-string",
            "min_complexity": self.config.get_rule_option(
                self.rule_id, "min_complexity", 2
            )
        }
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        issues = []
        results = PylintHelper.check_source(source, self.pylint_config)
        
        for item in results:
            if item.get("message-id") == "W1308" or "f-string" in item.get("message", "").lower():
                issues.append(Issue(
                    rule_id=self.rule_id,
                    file=path,
                    line=item.get("line", 0),
                    col=item.get("column", 0),
                    message=item.get("message", "Consider using f-string"),
                    severity=Severity.INFO,
                    original="string concatenation"
                ))
        
        return issues
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        # Delegate to string transformation rules
        from prefact.rules.string_transformations import StringConcatToFString
        transformer = StringConcatToFString(self.config)
        return transformer.fix(path, source, issues)
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        # Check if string concatenations remain
        results = PylintHelper.check_source(fixed, self.pylint_config)
        remaining = [
            r for r in results 
            if r.get("message-id") == "W1308" or "f-string" in r.get("message", "").lower()
        ]
        
        return ValidationResult(
            file=path,
            passed=len(remaining) == 0,
            checks=["no_string_concat"] if not remaining else [],
            errors=[f"Still has {len(remaining)} string concatenations"] if remaining else []
        )


# Custom Pylint checker implementation
class PrefactPylintPlugin:
    """Custom Pylint plugin for prefact-specific checks."""
    
    @staticmethod
    def register(linter):
        """Register the custom checker with Pylint."""
        # This would be used if creating a proper Pylint plugin
        pass


# Advanced: Pylint-based comprehensive analysis
@register
class PylintComprehensive(BaseRule):
    """Comprehensive analysis using Pylint with custom rules."""
    
    rule_id = "pylint-comprehensive"
    description = "Run comprehensive Pylint analysis with prefact rules"
    
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.pylint_config = self._load_pylint_config()
    
    def _load_pylint_config(self) -> Dict:
        """Load comprehensive Pylint configuration."""
        return {
            "enable_codes": self.config.get_rule_option(
                self.rule_id, "enable_codes",
                "print-statement,consider-using-f-string,unused-import,"
                "duplicate-key,unnecessary-comprehension"
            ),
            "disable_codes": self.config.get_rule_option(
                self.rule_id, "disable_codes", ""
            ),
            "score": self.config.get_rule_option(
                self.rule_id, "score", False
            )
        }
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        issues = []
        results = PylintHelper.check_source(source, self.pylint_config)
        
        for item in results:
            # Map Pylint message IDs to prefact rule IDs
            rule_id = self._map_pylint_to_prefact(item.get("message-id", ""))
            
            if rule_id:
                severity = self._map_pylint_severity(item.get("type", ""))
                
                issues.append(Issue(
                    rule_id=rule_id,
                    file=path,
                    line=item.get("line", 0),
                    col=item.get("column", 0),
                    message=item.get("message", ""),
                    severity=severity,
                    original=item.get("symbol", "")
                ))
        
        return issues
    
    def _map_pylint_to_prefact(self, pylint_id: str) -> Optional[str]:
        """Map Pylint message IDs to prefact rule IDs."""
        mapping = {
            "W1201": "print-statements",
            "W1308": "string-concat",
            "W0611": "unused-imports",
            "W0123": "duplicate-imports",
            "W0108": "unnecessary-lambda",
            "C0200": "consider-using-enumerate",
        }
        return mapping.get(pylint_id)
    
    def _map_pylint_severity(self, pylint_type: str) -> Severity:
        """Map Pylint message types to prefact severities."""
        mapping = {
            "error": Severity.ERROR,
            "warning": Severity.WARNING,
            "refactor": Severity.INFO,
            "convention": Severity.INFO,
            "info": Severity.INFO,
        }
        return mapping.get(pylint_type.lower(), Severity.INFO)
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        # Delegate to appropriate fixers based on rule types
        all_fixes = []
        fixed_source = source
        
        # Group issues by rule type
        issues_by_rule = {}
        for issue in issues:
            if issue.rule_id not in issues_by_rule:
                issues_by_rule[issue.rule_id] = []
            issues_by_rule[issue.rule_id].append(issue)
        
        # Apply fixes for each rule type
        for rule_id, rule_issues in issues_by_rule.items():
            if rule_id == "print-statements":
                fixed, fixes = PylintPrintStatements(self.config).fix(
                    path, fixed_source, rule_issues
                )
            elif rule_id == "string-concat":
                fixed, fixes = PylintStringConcat(self.config).fix(
                    path, fixed_source, rule_issues
                )
            else:
                fixed, fixes = fixed_source, []
            
            fixed_source = fixed
            all_fixes.extend(fixes)
        
        return fixed_source, all_fixes
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        # Run comprehensive validation
        all_checks = []
        all_errors = []
        
        # Check each rule type
        rule_types = ["print-statements", "string-concat", "unused-imports"]
        
        for rule_type in rule_types:
            results = PylintHelper.check_source(fixed, {"enable_codes": rule_type})
            if not results:
                all_checks.append(f"no_{rule_type}")
            else:
                all_errors.append(f"Still has {len(results)} {rule_type}")
        
        return ValidationResult(
            file=path,
            passed=len(all_errors) == 0,
            checks=all_checks,
            errors=all_errors
        )


# Pylint configuration generator
def generate_pylint_rc(config: Config, output_path: Path) -> None:
    """Generate a .pylintrc file based on prefact configuration."""
    content = """[MAIN]
disable=all

[MESSAGES CONTROL]
enable=print-statement,consider-using-f-string,unused-import,duplicate-key

[FORMAT]
max-line-length=88

[DESIGN]
max-args=7
max-locals=15
max-returns=6
max-branches=12
max-statements=50
max-parents=7
max-attributes=7
min-public-methods=2
max-public-methods=20

[TYPECHECK]
ignored-modules=
ignored-classes=
generated-members=

"""
    
    # Add custom configurations
    for rule_id, rule_config in config.rules.items():
        if rule_config.options:
            content += f"\n[{rule_id.upper()}]\n"
            for key, value in rule_config.options.items():
                content += f"{key}={value}\n"
    
    output_path.write_text(content)
