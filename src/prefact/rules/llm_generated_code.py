"""LLM generated code detection rule.

This module provides rules to detect patterns typical of
LLM-generated code.
"""

import ast
import re
from pathlib import Path
from typing import List

from prefact.config import Config
from prefact.models import Fix, Issue, Severity, ValidationResult
from prefact.rules import BaseRule, register


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
