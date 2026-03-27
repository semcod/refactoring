"""Factory for creating composite rules dynamically.

This module provides utilities for creating composite rules
based on configuration.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Type

from prefact.config import Config
from prefact.models import Fix, Issue, ValidationResult
from prefact.rules import BaseRule, get_all_rules, register
from prefact.rules.strategies import (
    ParallelScanStrategy,
    SequentialScanStrategy,
    PriorityBasedStrategy,
    ToolStrategy
)


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
