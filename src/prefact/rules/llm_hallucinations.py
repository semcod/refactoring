"""LLM hallucination detection rule.

This module provides rules to detect potential LLM hallucinations
in generated code.
"""

import ast
import re
from pathlib import Path
from typing import List

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
