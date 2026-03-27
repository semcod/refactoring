"""Migrating existing AST-based rules to Ruff-based implementations.

This module shows how to gradually replace existing rules with Ruff equivalents
while maintaining backward compatibility.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Type

from prefact.config import Config
from prefact.models import Issue
from prefact.rules import BaseRule, get_all_rules


class RuleMigrationManager:
    """Manages migration from AST-based rules to Ruff-based rules."""
    
    # Mapping of old rule IDs to new Ruff-based rule class names
    # (using strings to avoid circular imports)
    MIGRATION_MAP: Dict[str, str] = {
        "unused-imports": "RuffUnusedImports",
        "duplicate-imports": "RuffDuplicateImports",
        "wildcard-imports": "RuffWildcardImports",
        "sorted-imports": "RuffSortedImports",
        "print-statements": "RuffPrintStatements",
    }
    
    # Rules that should remain AST-based (Ruff doesn't handle them well)
    KEEP_AST_RULES = {
        "relative-imports",  # Requires package context
        "string-concat",     # Complex transformation
        "missing-return-type",  # Type checking needed
    }
    
    def __init__(self, config: Config) -> None:
        self.config = config
        self._migrated_rules: Dict[str, Type[BaseRule]] = {}
        
    def get_migrated_rule(self, rule_id: str) -> Type[BaseRule]:
        """Get the Ruff-based rule if available, otherwise return None."""
        if rule_id in self.MIGRATION_MAP:
            if rule_id not in self._migrated_rules:
                # Lazy import to avoid circular dependency
                from prefact.rules.ruff_based import (
                    RuffDuplicateImports,
                    RuffPrintStatements,
                    RuffSortedImports,
                    RuffUnusedImports,
                    RuffWildcardImports,
                )
                
                rule_classes = {
                    "RuffUnusedImports": RuffUnusedImports,
                    "RuffDuplicateImports": RuffDuplicateImports,
                    "RuffWildcardImports": RuffWildcardImports,
                    "RuffSortedImports": RuffSortedImports,
                    "RuffPrintStatements": RuffPrintStatements,
                }
                
                class_name = self.MIGRATION_MAP[rule_id]
                self._migrated_rules[rule_id] = rule_classes[class_name]
            return self._migrated_rules[rule_id]
        return None
    
    def should_use_ruff(self, rule_id: str) -> bool:
        """Check if a rule should use Ruff implementation."""
        return (
            rule_id in self.MIGRATION_MAP and 
            rule_id not in self.KEEP_AST_RULES and
            self.config.get_rule_option(rule_id, "use_ruff", True)
        )
    
    def create_hybrid_rule(self, rule_id: str) -> Type[BaseRule]:
        """Create a hybrid rule that can switch between AST and Ruff."""
        if rule_id not in self.MIGRATION_MAP:
            return get_all_rules().get(rule_id)
        
        class HybridRule(BaseRule):
            rule_id = rule_id
            description = f"Hybrid implementation for {rule_id}"
            
            def __init__(self, config: Config) -> None:
                super().__init__(config)
                self.migration_manager = RuleMigrationManager(config)
                self.ast_rule = get_all_rules().get(rule_id)(config)
                self.ruff_rule = self.MIGRATION_MAP[rule_id](config)
                
            def scan_file(self, path: Path, source: str) -> List[Issue]:
                if self.migration_manager.should_use_ruff(rule_id):
                    return self.ruff_rule.scan_file(path, source)
                return self.ast_rule.scan_file(path, source)
                
            def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List]:
                if self.migration_manager.should_use_ruff(rule_id):
                    return self.ruff_rule.fix(path, source, issues)
                return self.ast_rule.fix(path, source, issues)
                
            def validate(self, path: Path, original: str, fixed: str):
                if self.migration_manager.should_use_ruff(rule_id):
                    return self.ruff_rule.validate(path, original, fixed)
                return self.ast_rule.validate(path, original, fixed)
        
        return HybridRule


# Example: Enhanced scanner with Ruff integration
class HybridScanner:
    """Scanner that can use both AST and Ruff-based rules."""
    
    def __init__(self, config: Config) -> None:
        self.config = config
        self.migration_manager = RuleMigrationManager(config)
        self.rules = self._load_rules()
        
    def _load_rules(self) -> Dict[str, BaseRule]:
        """Load rules, preferring Ruff implementations where available."""
        rules = {}
        all_rule_classes = get_all_rules()
        
        for rule_id, rule_class in all_rule_classes.items():
            if self.migration_manager.should_use_ruff(rule_id):
                # Use Ruff-based rule
                ruff_rule = self.migration_manager.get_migrated_rule(rule_id)
                if ruff_rule:
                    rules[rule_id] = ruff_rule(self.config)
                    continue
            
            # Use original AST-based rule
            if rule_id not in RuleMigrationManager.KEEP_AST_RULES:
                rules[rule_id] = rule_class(self.config)
        
        return rules
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        """Scan a file using appropriate rules."""
        all_issues = []
        
        for rule_id, rule in self.rules.items():
            if self.config.is_rule_enabled(rule_id):
                issues = rule.scan_file(path, source)
                all_issues.extend(issues)
        
        return all_issues


# Performance comparison utilities
class PerformanceProfiler:
    """Compare performance between AST and Ruff implementations."""
    
    @staticmethod
    def profile_rule(rule: BaseRule, file_path: Path, source: str) -> Dict:
        """Profile a single rule execution."""
        import time
        
        start_time = time.perf_counter()
        issues = rule.scan_file(file_path, source)
        end_time = time.perf_counter()
        
        return {
            "rule_id": rule.rule_id,
            "issues_found": len(issues),
            "time_ms": (end_time - start_time) * 1000,
            "implementation": rule.__class__.__module__
        }
    
    @staticmethod
    def compare_implementations(
        file_path: Path, 
        source: str,
        config: Config
    ) -> Dict[str, Dict]:
        """Compare AST vs Ruff implementations for applicable rules."""
        results = {}
        migration_manager = RuleMigrationManager(config)
        
        for rule_id in migration_manager.MIGRATION_MAP:
            # Get AST implementation
            ast_rule_class = get_all_rules().get(rule_id)
            if not ast_rule_class:
                continue
                
            # Get Ruff implementation
            ruff_rule_class = migration_manager.get_migrated_rule(rule_id)
            if not ruff_rule_class:
                continue
            
            # Profile both
            ast_rule = ast_rule_class(config)
            ruff_rule = ruff_rule_class(config)
            
            results[rule_id] = {
                "ast": PerformanceProfiler.profile_rule(ast_rule, file_path, source),
                "ruff": PerformanceProfiler.profile_rule(ruff_rule, file_path, source)
            }
            
            # Calculate speedup
            ast_time = results[rule_id]["ast"]["time_ms"]
            ruff_time = results[rule_id]["ruff"]["time_ms"]
            if ruff_time > 0:
                results[rule_id]["speedup"] = ast_time / ruff_time
        
        return results


# Configuration for enabling Ruff-based rules
def add_ruff_config_to_pprefact_yaml(config_path: Path) -> None:
    """Add Ruff-specific configuration to pprefact.yaml."""
    import yaml
    
    with open(config_path) as f:
        config = yaml.safe_load(f) or {}
    
    # Add Ruff settings
    if "ruff" not in config:
        config["ruff"] = {
            "enabled": True,
            "rules": {
                "unused-imports": {"use_ruff": True},
                "wildcard-imports": {"use_ruff": True},
                "print-statements": {"use_ruff": True},
                "sorted-imports": {"use_ruff": True},
                "duplicate-imports": {"use_ruff": True},
            },
            "ignore_patterns": ["cli.py", "scripts/"]  # For print statements
        }
    
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)
