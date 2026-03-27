"""LLM-specific rules for prefact.

This module provides rules specifically designed to detect patterns
commonly found in LLM-generated code and other AI-related issues.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import List, Optional, Set

from prefact.config import Config
from prefact.models import Fix, Issue, Severity, ValidationResult
from prefact.rules import BaseRule, register


@register
class LLMHallucinationRule(BaseRule):
    """Detect LLM hallucination patterns in code."""
    
    rule_id = "llm-hallucinations"
    description = "Detect potential LLM hallucinations in code"
    
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.patterns = self._load_patterns()
    
    def _load_patterns(self) -> List[dict]:
        """Load hallucination patterns from configuration."""
        default_patterns = [
            {
                "pattern": r"TODO: implement this properly",
                "severity": "warning",
                "message": "TODO comment - likely incomplete implementation"
            },
            {
                "pattern": r"placeholder code",
                "severity": "error",
                "message": "Placeholder code detected"
            },
            {
                "pattern": r"from [a-z]+\.llm\.generator import",
                "severity": "error",
                "message": "Suspicious LLM-related import - may be hallucinated"
            },
            {
                "pattern": r"from openai\.api import",
                "severity": "error",
                "message": "Incorrect OpenAI import - API has changed"
            },
            {
                "pattern": r"# This is a (template|example|placeholder)",
                "severity": "warning",
                "message": "Template/placeholder code detected"
            },
            {
                "pattern": r"raise NotImplementedError\(",
                "severity": "warning",
                "message": "NotImplementedError - incomplete implementation"
            },
            {
                "pattern": r"pass  # TODO",
                "severity": "warning",
                "message": "TODO with pass statement"
            },
            {
                "pattern": r"# FIXME: ",
                "severity": "info",
                "message": "FIXME comment - known issue"
            },
            {
                "pattern": r"# XXX: ",
                "severity": "warning",
                "message": "XXX comment - attention needed"
            },
            {
                "pattern": r"import (nonexistent|fake|dummy)_module",
                "severity": "error",
                "message": "Import of non-existent module detected"
            }
        ]
        
        return self.config.get_rule_option(
            self.rule_id, 
            "patterns", 
            default_patterns
        )
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        issues = []
        lines = source.splitlines()
        
        for line_num, line in enumerate(lines, 1):
            for pattern_config in self.patterns:
                pattern = pattern_config["pattern"]
                severity_str = pattern_config.get("severity", "warning")
                message = pattern_config.get("message", f"Pattern matched: {pattern}")
                
                if re.search(pattern, line, re.IGNORECASE):
                    severity = self._map_severity(severity_str)
                    
                    issues.append(Issue(
                        rule_id=self.rule_id,
                        file=path,
                        line=line_num,
                        col=0,
                        message=message,
                        severity=severity,
                        original=line.strip()
                    ))
        
        # Additional AST-based checks
        issues.extend(self._check_ast_patterns(path, source))
        
        return issues
    
    def _check_ast_patterns(self, path: Path, source: str) -> List[Issue]:
        """Check for patterns in AST."""
        issues = []
        
        try:
            tree = ast.parse(source)
            
            for node in ast.walk(tree):
                # Check for suspicious function names
                if isinstance(node, ast.FunctionDef):
                    if self._is_suspicious_function_name(node.name):
                        issues.append(Issue(
                            rule_id=self.rule_id,
                            file=path,
                            line=node.lineno,
                            col=node.col_offset,
                            message=f"Suspicious function name: {node.name}",
                            severity=Severity.WARNING,
                            original=node.name
                        ))
                
                # Check for suspicious imports
                elif isinstance(node, ast.ImportFrom):
                    if self._is_suspicious_import(node):
                        module = node.module or ""
                        issues.append(Issue(
                            rule_id=self.rule_id,
                            file=path,
                            line=node.lineno,
                            col=node.col_offset,
                            message=f"Suspicious import: from {module}",
                            severity=Severity.ERROR,
                            original=module
                        ))
                
        except SyntaxError:
            pass
        
        return issues
    
    def _is_suspicious_function_name(self, name: str) -> bool:
        """Check if function name looks suspicious."""
        suspicious_patterns = [
            r"placeholder_",
            r"dummy_",
            r"fake_",
            r"temp_",
            r"test_.*_func",  # Test function in production code
            r"example_",
            r"sample_",
        ]
        
        return any(re.match(pattern, name) for pattern in suspicious_patterns)
    
    def _is_suspicious_import(self, node: ast.ImportFrom) -> bool:
        """Check if import looks suspicious."""
        module = node.module or ""
        
        suspicious_modules = [
            "nonexistent",
            "fake",
            "dummy",
            "placeholder",
            "example",
            "sample",
            "openai.api",  # Old API
            "langchain.experimental",  # Experimental features
        ]
        
        return any(sus in module for sus in suspicious_modules)
    
    def _map_severity(self, severity_str: str) -> Severity:
        """Map string severity to Severity enum."""
        mapping = {
            "error": Severity.ERROR,
            "warning": Severity.WARNING,
            "info": Severity.INFO,
        }
        return mapping.get(severity_str, Severity.WARNING)
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        # Hallucinations usually require manual review
        return source, []
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        # Re-scan to check if issues remain
        remaining = self.scan_file(path, fixed)
        
        return ValidationResult(
            file=path,
            passed=len(remaining) == 0,
            checks=["no_hallucinations"] if not remaining else [],
            errors=[f"Still has {len(remaining)} hallucination patterns"] if remaining else []
        )


@register
class MagicNumberRule(BaseRule):
    """Detect magic numbers in code."""
    
    rule_id = "magic-numbers"
    description = "Detect magic numbers that should be named constants"
    
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.allowed_numbers = self._load_allowed_numbers()
        self.threshold = self.config.get_rule_option(self.rule_id, "threshold", 10)
        self.ignore_patterns = self.config.get_rule_option(
            self.rule_id, 
            "ignore_patterns", 
            [r"test_.*\.py", r".*_test\.py"]
        )
    
    def _load_allowed_numbers(self) -> Set[int]:
        """Load allowed magic numbers."""
        default_allowed = {0, 1, -1, 2, 10, 100, 1000}
        return set(
            self.config.get_rule_option(
                self.rule_id, 
                "allowed_numbers", 
                list(default_allowed)
            )
        )
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        issues = []
        
        # Skip test files if configured
        if any(re.match(pattern, path.name) for pattern in self.ignore_patterns):
            return issues
        
        try:
            tree = ast.parse(source)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant):
                    if isinstance(node.value, (int, float)):
                        if self._is_magic_number(node.value):
                            issues.append(Issue(
                                rule_id=self.rule_id,
                                file=path,
                                line=node.lineno,
                                col=node.col_offset,
                                message=f"Magic number: {node.value} - use named constant",
                                severity=Severity.INFO,
                                original=str(node.value),
                                suggested=f"CONSTANT_NAME"
                            ))
                elif isinstance(node, ast.Num):  # For older Python versions
                    if self._is_magic_number(node.n):
                        issues.append(Issue(
                            rule_id=self.rule_id,
                            file=path,
                            line=node.lineno,
                            col=node.col_offset,
                            message=f"Magic number: {node.n} - use named constant",
                            severity=Severity.INFO,
                            original=str(node.n),
                            suggested=f"CONSTANT_NAME"
                        ))
                
                # Check for magic numbers in comparisons
                elif isinstance(node, ast.Compare):
                    for comparator in node.comparators:
                        if isinstance(comparator, ast.Constant) and isinstance(comparator.value, (int, float)):
                            if self._is_magic_number(comparator.value):
                                issues.append(Issue(
                                    rule_id=self.rule_id,
                                    file=path,
                                    line=node.lineno,
                                    col=node.col_offset,
                                    message=f"Magic number in comparison: {comparator.value}",
                                    severity=Severity.INFO,
                                    original=str(comparator.value)
                                ))
        
        except SyntaxError:
            pass
        
        return issues
    
    def _is_magic_number(self, value: int | float) -> bool:
        """Check if a number is a magic number."""
        # Skip allowed numbers
        if value in self.allowed_numbers:
            return False
        
        # Skip very small numbers
        if abs(value) < self.threshold:
            return False
        
        # Skip common multipliers
        if value in {24, 60, 3600, 86400}:  # Time units
            return False
        
        # Skip powers of 2 (common in programming)
        if isinstance(value, int) and value > 0 and (value & (value - 1)) == 0:
            return False
        
        return True
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        # Magic numbers require manual naming
        return source, []
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        issues = self.scan_file(path, fixed)
        
        return ValidationResult(
            file=path,
            passed=len(issues) == 0,
            checks=["no_magic_numbers"] if not issues else [],
            errors=[f"Still has {len(issues)} magic numbers"] if issues else []
        )


@register
class LLMGeneratedCodeRule(BaseRule):
    """Detect code that appears to be LLM-generated."""
    
    rule_id = "llm-generated-code"
    description = "Detect patterns typical of LLM-generated code"
    
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.indicators = self._load_indicators()
    
    def _load_indicators(self) -> List[dict]:
        """Load LLM generation indicators."""
        return [
            {
                "pattern": r"Here'?s? (a|the) (simple|basic) (example|implementation)",
                "severity": "info",
                "message": "Typical LLM introductory phrase"
            },
            {
                "pattern": r"Note that this (code|implementation)",
                "severity": "info",
                "message": "LLM explanatory comment"
            },
            {
                "pattern": r"# (In this example|For example|For instance)",
                "severity": "info",
                "message": "LLM example comment"
            },
            {
                "pattern": r"def (example_|sample_|demo_)",
                "severity": "warning",
                "message": "Example function in production code"
            },
            {
                "pattern": r"class (Example|Sample|Demo)",
                "severity": "warning",
                "message": "Example class in production code"
            },
            {
                "pattern": r"# (You can|You may|One can)",
                "severity": "info",
                "message": "LLM instructional comment"
            },
            {
                "pattern": r"# (Make sure|Ensure that|Be sure to)",
                "severity": "info",
                "message": "LLM reminder comment"
            }
        ]
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        issues = []
        lines = source.splitlines()
        
        # Check for LLM indicators
        for line_num, line in enumerate(lines, 1):
            for indicator in self.indicators:
                if re.search(indicator["pattern"], line, re.IGNORECASE):
                    severity = self._map_severity(indicator.get("severity", "info"))
                    
                    issues.append(Issue(
                        rule_id=self.rule_id,
                        file=path,
                        line=line_num,
                        col=0,
                        message=indicator["message"],
                        severity=severity,
                        original=line.strip()
                    ))
        
        # Check for excessive comments (LLM tends to over-comment)
        issues.extend(self._check_comment_ratio(path, source))
        
        # Check for docstring patterns
        issues.extend(self._check_docstring_patterns(path, source))
        
        return issues
    
    def _check_comment_ratio(self, path: Path, source: str) -> List[Issue]:
        """Check if code has too many comments (LLM tendency)."""
        issues = []
        lines = source.splitlines()
        
        code_lines = 0
        comment_lines = 0
        
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                code_lines += 1
            elif stripped.startswith("#"):
                comment_lines += 1
        
        # If comment ratio is too high
        if code_lines > 10 and comment_lines / code_lines > 0.5:
            issues.append(Issue(
                rule_id=self.rule_id,
                file=path,
                line=1,
                col=0,
                message=f"High comment-to-code ratio: {comment_lines}/{code_lines}",
                severity=Severity.INFO,
                original=f"Comment ratio: {comment_lines/code_lines:.2f}"
            ))
        
        return issues
    
    def _check_docstring_patterns(self, path: Path, source: str) -> List[Issue]:
        """Check for LLM-typical docstring patterns."""
        issues = []
        
        try:
            tree = ast.parse(source)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    if (ast.get_docstring(node) and 
                        self._has_llm_docstring_pattern(ast.get_docstring(node) or "")):
                        
                        issues.append(Issue(
                            rule_id=self.rule_id,
                            file=path,
                            line=node.lineno,
                            col=node.col_offset,
                            message=f"LLM-style docstring in {node.name}",
                            severity=Severity.INFO,
                            original=node.name
                        ))
        
        except SyntaxError:
            pass
        
        return issues
    
    def _has_llm_docstring_pattern(self, docstring: str) -> bool:
        """Check if docstring has LLM patterns."""
        llm_patterns = [
            r"This function (takes|receives|accepts)",
            r"This function (returns|yields)",
            r"Args:",
            r"Returns:",
            r"Example:",
            r"Note:",
            r"Please note:",
        ]
        
        return any(re.search(pattern, docstring, re.IGNORECASE) for pattern in llm_patterns)
    
    def _map_severity(self, severity_str: str) -> Severity:
        """Map string severity to Severity enum."""
        mapping = {
            "error": Severity.ERROR,
            "warning": Severity.WARNING,
            "info": Severity.INFO,
        }
        return mapping.get(severity_str, Severity.INFO)
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        # LLM patterns require manual review
        return source, []
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        issues = self.scan_file(path, fixed)
        
        return ValidationResult(
            file=path,
            passed=len(issues) == 0,
            checks=["no_llm_patterns"] if not issues else [],
            errors=[f"Still has {len(issues)} LLM patterns"] if issues else []
        )


@register
class AIBoilerplateRule(BaseRule):
    """Detect AI boilerplate and template code."""
    
    rule_id = "ai-boilerplate"
    description = "Detect AI boilerplate and template code"
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        issues = []
        
        # Check for common AI boilerplate
        boilerplate_patterns = [
            (r"# (Copyright|License|MIT)", "boilerplate copyright"),
            (r"# Author: .*(AI|ChatGPT|Claude|Bard)", "AI author attribution"),
            (r"# Generated by .*AI", "AI generation attribution"),
            (r"def main\(\):", "standalone main function"),
            (r"if __name__ == ['\"]__main__['\"]:", "module execution block"),
        ]
        
        lines = source.splitlines()
        for line_num, line in enumerate(lines, 1):
            for pattern, message in boilerplate_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(Issue(
                        rule_id=self.rule_id,
                        file=path,
                        line=line_num,
                        col=0,
                        message=message,
                        severity=Severity.INFO,
                        original=line.strip()
                    ))
        
        return issues
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        # Boilerplate removal requires manual decision
        return source, []
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        issues = self.scan_file(path, fixed)
        
        return ValidationResult(
            file=path,
            passed=len(issues) == 0,
            checks=["no_boilerplate"] if not issues else [],
            errors=[f"Still has {len(issues)} boilerplate"] if issues else []
        )
