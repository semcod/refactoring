"""Composite rules that combine multiple tools for comprehensive analysis.

This module provides composite rules that orchestrate multiple tools
to provide more comprehensive code analysis and fixing.
"""

from __future__ import annotations

import concurrent.futures
from abc import ABC, abstractmethod
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Type

from prefact.config import Config
from prefact.models import Fix, Issue, Severity, ValidationResult
from prefact.rules import BaseRule, get_all_rules, register


class ToolStrategy(ABC):
    """Abstract base class for tool orchestration strategies."""
    
    @abstractmethod
    def scan(self, path: Path, source: str, tools: List[BaseRule]) -> List[Issue]:
        """Scan using multiple tools."""
        pass
    
    @abstractmethod
    def fix(self, path: Path, source: str, issues: List[Issue], tools: List[BaseRule]) -> Tuple[str, List[Fix]]:
        """Fix issues using multiple tools."""
        pass


class ParallelScanStrategy(ToolStrategy):
    """Run all tools in parallel and merge results."""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
    
    def scan(self, path: Path, source: str, tools: List[BaseRule]) -> List[Issue]:
        """Scan with all tools in parallel."""
        all_issues = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all scan tasks
            future_to_tool = {
                executor.submit(tool.scan_file, path, source): tool
                for tool in tools
            }
            
            # Collect results
            for future in concurrent.futures.as_completed(future_to_tool):
                tool = future_to_tool[future]
                try:
                    issues = future.result()
                    all_issues.extend(issues)
                except Exception as e:
                    # Log error but continue with other tools
                    print(f"Error in {tool.rule_id}: {e}")
        
        return all_issues
    
    def fix(self, path: Path, source: str, issues: List[Issue], tools: List[BaseRule]) -> Tuple[str, List[Fix]]:
        """Apply fixes sequentially (order matters for fixes)."""
        current_source = source
        all_fixes = []
        
        # Group issues by rule ID
        issues_by_rule = defaultdict(list)
        for issue in issues:
            issues_by_rule[issue.rule_id].append(issue)
        
        # Apply fixes in tool priority order
        for tool in tools:
            rule_issues = issues_by_rule.get(tool.rule_id, [])
            if rule_issues:
                fixed_source, fixes = tool.fix(path, current_source, rule_issues)
                if fixed_source != current_source:
                    current_source = fixed_source
                    all_fixes.extend(fixes)
        
        return current_source, all_fixes


class SequentialScanStrategy(ToolStrategy):
    """Run tools sequentially, passing results between them."""
    
    def scan(self, path: Path, source: str, tools: List[BaseRule]) -> List[Issue]:
        """Scan with tools in sequence."""
        all_issues = []
        current_source = source
        
        for tool in tools:
            issues = tool.scan_file(path, current_source)
            all_issues.extend(issues)
            
            # Optionally apply fixes between scans
            if hasattr(tool, 'auto_fix') and tool.auto_fix:
                current_source, _ = tool.fix(path, current_source, issues)
        
        return all_issues
    
    def fix(self, path: Path, source: str, issues: List[Issue], tools: List[BaseRule]) -> Tuple[str, List[Fix]]:
        """Fix using tools in sequence."""
        return ParallelScanStrategy().fix(path, source, issues, tools)


class PriorityBasedStrategy(ToolStrategy):
    """Use tool priority to resolve conflicts."""
    
    def __init__(self, tool_priorities: Dict[str, int]):
        self.tool_priorities = tool_priorities
    
    def scan(self, path: Path, source: str, tools: List[BaseRule]) -> List[Issue]:
        """Scan with all tools and resolve conflicts by priority."""
        all_issues = []
        
        # Group issues by location
        issues_by_location = defaultdict(list)
        
        # Scan with all tools
        for tool in tools:
            issues = tool.scan_file(path, source)
            for issue in issues:
                key = (issue.file, issue.line, issue.rule_id)
                issues_by_location[key].append((issue, tool))
        
        # Resolve conflicts
        for key, issue_list in issues_by_location.items():
            if len(issue_list) == 1:
                all_issues.append(issue_list[0][0])
            else:
                # Choose issue from highest priority tool
                best_issue = max(
                    issue_list,
                    key=lambda x: self.tool_priorities.get(x[1].rule_id, 0)
                )[0]
                all_issues.append(best_issue)
        
        return all_issues
    
    def fix(self, path: Path, source: str, issues: List[Issue], tools: List[BaseRule]) -> Tuple[str, List[Fix]]:
        """Fix using tools in priority order."""
        # Sort tools by priority
        sorted_tools = sorted(
            tools,
            key=lambda t: self.tool_priorities.get(t.rule_id, 0),
            reverse=True
        )
        
        return ParallelScanStrategy().fix(path, source, issues, sorted_tools)


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


# Advanced: Dynamic composite rule factory
class CompositeRuleFactory:
    """Factory for creating composite rules dynamically."""
    
    @staticmethod
    def create_composite_rule(
        rule_id: str,
        description: str,
        tool_ids: List[str],
        config: Config,
        strategy: str = "parallel"
    ) -> Type[BaseRule]:
        """Create a composite rule dynamically."""
        
        class DynamicCompositeRule(BaseRule):
            rule_id = rule_id
            description = description
            
            def __init__(self, config: Config) -> None:
                super().__init__(config)
                self.strategy = self._create_strategy(strategy)
                self.tools = self._load_tools(tool_ids)
            
            def _create_strategy(self, strategy_type: str) -> ToolStrategy:
                if strategy_type == "sequential":
                    return SequentialScanStrategy()
                elif strategy_type == "priority":
                    priorities = config.get_rule_option(
                        rule_id, "tool_priorities", {}
                    )
                    return PriorityBasedStrategy(priorities)
                else:
                    max_workers = config.get_rule_option(
                        rule_id, "max_workers", 4
                    )
                    return ParallelScanStrategy(max_workers)
            
            def _load_tools(self, tool_ids: List[str]) -> List[BaseRule]:
                tools = []
                all_rules = get_all_rules()
                
                for tool_id in tool_ids:
                    if tool_id in all_rules:
                        tool_class = all_rules[tool_id]
                        tools.append(tool_class(config))
                
                return tools
            
            def scan_file(self, path: Path, source: str) -> List[Issue]:
                if not self.tools:
                    return []
                return self.strategy.scan(path, source, self.tools)
            
            def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
                if not self.tools:
                    return source, []
                return self.strategy.fix(path, source, issues, self.tools)
            
            def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
                if not self.tools:
                    return ValidationResult(file=path, passed=True, checks=[], errors=[])
                
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
        
        return DynamicCompositeRule


# Utility: Register composite rules from configuration
def register_composite_rules(config: Config) -> None:
    """Register composite rules defined in configuration."""
    composite_rules = config.get_rule_option("_composite", "rules", [])
    
    for rule_def in composite_rules:
        rule_id = rule_def.get("id")
        description = rule_def.get("description", "")
        tool_ids = rule_def.get("tools", [])
        strategy = rule_def.get("strategy", "parallel")
        
        if rule_id and tool_ids:
            rule_class = CompositeRuleFactory.create_composite_rule(
                rule_id, description, tool_ids, config, strategy
            )
            register(rule_class)
