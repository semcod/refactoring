"""Custom rule: Detect TODO comments in code."""

import ast
import re
from pathlib import Path
from typing import List

from prefact.config import Config
from prefact.models import Fix, Issue, Severity, ValidationResult
from prefact.rules import BaseRule, register


@register
class NoTodoRule(BaseRule):
    """Rule that detects TODO comments in code."""
    
    rule_id = "no-todo"
    description = "Detect TODO comments in code"
    
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        # Pattern to match TODO comments
        self.todo_pattern = re.compile(r'#\s*TODO\s*:?\s*(.+)', re.IGNORECASE)
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        """Scan for TODO comments."""
        issues = []
        lines = source.split('\n')
        
        for lineno, line in enumerate(lines, 1):
            match = self.todo_pattern.search(line)
            if match:
                issue = Issue(
                    rule_id=self.rule_id,
                    path=path,
                    line=lineno,
                    column=line.find('#'),
                    message=f"TODO comment found: {match.group(1).strip()}",
                    severity=Severity.INFO,
                    fixable=False  # This rule only detects, doesn't fix
                )
                issues.append(issue)
        
        return issues
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        """This rule doesn't auto-fix TODOs."""
        return source, []
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        """Validate that the code is still valid."""
        try:
            ast.parse(fixed)
            return ValidationResult(valid=True, message="Code is valid")
        except SyntaxError as e:
            return ValidationResult(
                valid=False,
                message=f"Syntax error: {e}",
                line=e.lineno
            )


@register  
class NoPrintRule(BaseRule):
    """Custom rule that detects print statements (alternative to built-in)."""
    
    rule_id = "custom-no-print"
    description = "Detect print statements in production code"
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        """Scan for print statements."""
        issues = []
        
        try:
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'print':
                    issue = Issue(
                        rule_id=self.rule_id,
                        path=path,
                        line=node.lineno,
                        column=node.col_offset,
                        message="Print statement detected in production code",
                        severity=Severity.WARNING,
                        fixable=False
                    )
                    issues.append(issue)
        except SyntaxError:
            # If we can't parse, skip this file
            pass
        
        return issues
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        """This rule doesn't auto-fix prints."""
        return source, []
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        """Validate that the code is still valid."""
        try:
            ast.parse(fixed)
            return ValidationResult(valid=True, message="Code is valid")
        except SyntaxError as e:
            return ValidationResult(
                valid=False,
                message=f"Syntax error: {e}",
                line=e.lineno
            )
