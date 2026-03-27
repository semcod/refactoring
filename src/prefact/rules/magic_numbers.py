"""Magic number detection rule.

This module provides rules to detect magic numbers in code
that should be named constants.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import List, Set

from prefact.config import Config
from prefact.models import Fix, Issue, Severity, ValidationResult
from prefact.rules import BaseRule, register


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
