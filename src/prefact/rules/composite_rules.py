"""Composite rules that combine multiple tools for comprehensive analysis.

This module provides composite rules that orchestrate multiple tools
to provide more comprehensive code analysis and fixing.
"""

from pathlib import Path
from typing import List

from prefact.config import Config
from prefact.models import Fix, Issue, ValidationResult
from prefact.rules import BaseRule, register
from prefact.rules.strategies import ParallelScanStrategy, ToolStrategy


@register
class CompositeUnusedImports(BaseRule):
    """Composite rule for unused imports using multiple tools."""
    
    rule_id = "composite-unused-imports"
    description = "Detect unused imports using multiple tools (Ruff, Pyflakes, Unimport)"
    
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.strategy = self._create_strategy()
        self.tools = self._load_tools()
    
    def _create_strategy(self) -> ToolStrategy:
        """Create the scan strategy based on configuration."""
        from prefact.rules.strategies import SequentialScanStrategy, PriorityBasedStrategy
        
        strategy_type = self.config.get_rule_option(
            self.rule_id, "strategy", "parallel"
        )
        
        if strategy_type == "sequential":
            return SequentialScanStrategy()
        elif strategy_type == "priority":
            priorities = self.config.get_rule_option(
                self.rule_id, "tool_priorities",
                {"ruff-unused-imports": 3, "unused-imports": 2, "unimport-unused-imports": 1}
            )
            return PriorityBasedStrategy(priorities)
        else:
            max_workers = self.config.get_rule_option(
                self.rule_id, "max_workers", 4
            )
            return ParallelScanStrategy(max_workers)
    
    def _load_tools(self) -> List[BaseRule]:
        """Load the tools to use."""
        tools = []
        
        # Try to load Ruff-based rule
        try:
            from prefact.rules.ruff_based import RuffUnusedImports
            if self.config.get_rule_option("unused-imports", "use_ruff", False):
                tools.append(RuffUnusedImports(self.config))
        except ImportError:
            pass
        
        # Load AST-based rule
        try:
            from prefact.rules.unused_imports import UnusedImports
            tools.append(UnusedImports(self.config))
        except ImportError:
            pass
        
        # Try to load Unimport-based rule
        try:
            from prefact.rules.unimport_based import UnimportUnusedImports
            tools.append(UnimportUnusedImports(self.config))
        except ImportError:
            pass
        
        return tools
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        """Scan using all configured tools."""
        if not self.tools:
            return []
        
        return self.strategy.scan(path, source, self.tools)
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        """Fix using the strategy."""
        if not self.tools:
            return source, []
        
        return self.strategy.fix(path, source, issues, self.tools)
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        """Validate using the highest priority tool."""
        if not self.tools:
            return ValidationResult(file=path, passed=True, checks=[], errors=[])
        
        # Use the first tool (highest priority) for validation
        return self.tools[0].validate(path, original, fixed)


@register
class CompositeImportRules(BaseRule):
    """Composite rule for all import-related checks."""
    
    rule_id = "composite-imports"
    description = "Comprehensive import analysis using multiple tools"
    
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.strategy = ParallelScanStrategy(max_workers=6)
        self.tools = self._load_tools()
    
    def _load_tools(self) -> List[BaseRule]:
        """Load all import-related tools."""
        tools = []
        
        # Unused imports
        if self.config.is_rule_enabled("unused-imports"):
            tools.extend(CompositeUnusedImports(self.config).tools)
        
        # Duplicate imports
        if self.config.is_rule_enabled("duplicate-imports"):
            try:
                from prefact.rules.duplicate_imports import DuplicateImports
                tools.append(DuplicateImports(self.config))
            except ImportError:
                pass
        
        # Wildcard imports
        if self.config.is_rule_enabled("wildcard-imports"):
            try:
                from prefact.rules.ruff_based import RuffWildcardImports
                tools.append(RuffWildcardImports(self.config))
            except ImportError:
                try:
                    from prefact.rules.wildcard_imports import WildcardImports
                    tools.append(WildcardImports(self.config))
                except ImportError:
                    pass
        
        # Sorted imports
        if self.config.is_rule_enabled("sorted-imports"):
            try:
                from prefact.rules.isort_based import ISortedImports
                tools.append(ISortedImports(self.config))
            except ImportError:
                try:
                    from prefact.rules.sorted_imports import SortedImports
                    tools.append(SortedImports(self.config))
                except ImportError:
                    pass
        
        # Relative imports
        if self.config.is_rule_enabled("relative-imports"):
            try:
                from prefact.rules.relative_imports import RelativeToAbsoluteImports
                tools.append(RelativeToAbsoluteImports(self.config))
            except ImportError:
                pass
        
        return tools
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        """Scan using all import tools."""
        if not self.tools:
            return []
        
        return self.strategy.scan(path, source, self.tools)
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        """Fix using appropriate tools."""
        if not self.tools:
            return source, []
        
        return self.strategy.fix(path, source, issues, self.tools)
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        """Validate all import rules."""
        all_checks = []
        all_errors = []
        
        for tool in self.tools:
            result = tool.validate(path, original, fixed)
            all_checks.extend(result.checks)
            all_errors.extend(result.errors)
        
        return ValidationResult(
            file=path,
            passed=len(all_errors) == 0,
            checks=all_checks,
            errors=all_errors
        )


@register
class CompositeTypeChecking(BaseRule):
    """Composite rule for type checking using multiple tools."""
    
    rule_id = "composite-type-checking"
    description = "Type checking using MyPy and Pylint"
    
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.tools = self._load_tools()
    
    def _load_tools(self) -> List[BaseRule]:
        """Load type checking tools."""
        tools = []
        
        # MyPy
        if self.config.is_rule_enabled("missing-return-type"):
            try:
                from prefact.rules.mypy_based import MyPyMissingReturnType
                tools.append(MyPyMissingReturnType(self.config))
            except ImportError:
                pass
        
        # Pylint type checking
        try:
            from prefact.rules.pylint_based import PylintComprehensive
            tools.append(PylintComprehensive(self.config))
        except ImportError:
            pass
        
        return tools
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        """Scan using all type checking tools."""
        if not self.tools:
            return []
        
        strategy = ParallelScanStrategy(max_workers=2)
        return strategy.scan(path, source, self.tools)
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        """Fix type-related issues."""
        if not self.tools:
            return source, []
        
        # Most type issues require manual fixes
        # We can only apply fixes for simple cases
        fixes = []
        
        for tool in self.tools:
            if hasattr(tool, 'fix'):
                fixed_source, tool_fixes = tool.fix(path, source, issues)
                if fixed_source != source:
                    source = fixed_source
                    fixes.extend(tool_fixes)
        
        return source, fixes
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        """Validate type checking."""
        all_checks = []
        all_errors = []
        
        for tool in self.tools:
            result = tool.validate(path, original, fixed)
            all_checks.extend(result.checks)
            all_errors.extend(result.errors)
        
        return ValidationResult(
            file=path,
            passed=len(all_errors) == 0,
            checks=all_checks,
            errors=all_errors
        )
