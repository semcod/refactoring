"""Lazy-loading rule registry for pprefact.

This module provides a lazy-loading registry to avoid importing all rule modules
at startup, significantly improving CLI cold-start performance.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Dict, List, Optional, Type, Union

from prefact.config import Config
from prefact.rules import BaseRule


class LazyRuleRegistry:
    """Registry that lazily loads rule classes."""
    
    def __init__(self):
        # Map rule IDs to module paths for lazy loading
        self._rule_modules: Dict[str, str] = {
            # Core AST-based rules
            "relative-imports": "pprefact.rules.relative_imports",
            "unused-imports": "pprefact.rules.unused_imports",
            "duplicate-imports": "pprefact.rules.duplicate_imports",
            "wildcard-imports": "pprefact.rules.wildcard_imports",
            "sorted-imports": "pprefact.rules.sorted_imports",
            "string-concat": "pprefact.rules.string_concat",
            "print-statements": "pprefact.rules.print_statements",
            "missing-return-type": "pprefact.rules.type_hints",
            
            # Ruff-based rules
            "ruff-unused-imports": "pprefact.rules.ruff_based",
            "ruff-duplicate-imports": "pprefact.rules.ruff_based",
            "ruff-wildcard-imports": "pprefact.rules.ruff_based",
            "ruff-print-statements": "pprefact.rules.ruff_based",
            "ruff-sorted-imports": "pprefact.rules.ruff_based",
            
            # MyPy-based rules
            "mypy-missing-return-type": "pprefact.rules.mypy_based",
            "mypy-type-checking": "pprefact.rules.mypy_based",
            "smart-return-type": "pprefact.rules.mypy_based",
            
            # ISort-based rules
            "isorted-imports": "pprefact.rules.isort_based",
            "import-section-separators": "pprefact.rules.isort_based",
            "custom-import-organization": "pprefact.rules.isort_based",
            
            # Autoflake-based rules
            "autoflake-unused-imports": "pprefact.rules.autoflake_based",
            "autoflake-unused-variables": "pprefact.rules.autoflake_based",
            "autoflake-duplicate-keys": "pprefact.rules.autoflake_based",
            "autoflake-all": "pprefact.rules.autoflake_based",
            
            # String transformation rules
            "string-concat-fstring": "pprefact.rules.string_transformations",
            "flynt-string-formatting": "pprefact.rules.string_transformations",
            "context-aware-string-concat": "pprefact.rules.string_transformations",
            
            # Pylint-based rules
            "pylint-print-statements": "pprefact.rules.pylint_based",
            "pylint-string-concat": "pprefact.rules.pylint_based",
            "pylint-comprehensive": "pprefact.rules.pylint_based",
            
            # Unimport-based rules
            "unimport-unused-imports": "pprefact.rules.unimport_based",
            "unimport-duplicate-imports": "pprefact.rules.unimport_based",
            "unimport-star-imports": "pprefact.rules.unimport_based",
            "unimport-all": "pprefact.rules.unimport_based",
            
            # ImportChecker-based rules
            "importchecker-unused-imports": "pprefact.rules.importchecker_based",
            "importchecker-duplicate-imports": "pprefact.rules.importchecker_based",
            "import-dependency-analysis": "pprefact.rules.importchecker_based",
            "import-optimizer": "pprefact.rules.importchecker_based",
            
            # Import-linter-based rules
            "import-linter-layers": "pprefact.rules.import_linter_based",
            "import-linter-no-relative": "pprefact.rules.import_linter_based",
            "import-linter-independence": "pprefact.rules.import_linter_based",
            "import-linter-custom-architecture": "pprefact.rules.import_linter_based",
            
            # Composite rules
            "composite-unused-imports": "pprefact.rules.composite",
            "composite-imports": "pprefact.rules.composite",
            "composite-type-checking": "pprefact.rules.composite",
        }
        
        # Cache for loaded rule classes
        self._rule_cache: Dict[str, Type[BaseRule]] = {}
        
        # Cache for loaded modules
        self._module_cache: Dict[str, object] = {}
    
    def get_rule(self, rule_id: str) -> Optional[Type[BaseRule]]:
        """Get a rule class, loading it if necessary."""
        if rule_id in self._rule_cache:
            return self._rule_cache[rule_id]
        
        if rule_id not in self._rule_modules:
            return None
        
        # Load the module
        module_path = self._rule_modules[rule_id]
        module = self._load_module(module_path)
        
        if module is None:
            return None
        
        # Find the rule class in the module
        rule_class = self._find_rule_class(module, rule_id)
        if rule_class:
            self._rule_cache[rule_id] = rule_class
            return rule_class
        
        return None
    
    def _load_module(self, module_path: str) -> Optional[object]:
        """Load a module and cache it."""
        if module_path in self._module_cache:
            return self._module_cache[module_path]
        
        try:
            module = importlib.import_module(module_path)
            self._module_cache[module_path] = module
            return module
        except ImportError as e:
            print(f"Warning: Could not load module {module_path}: {e}")
            return None
    
    def _find_rule_class(self, module, rule_id: str) -> Optional[Type[BaseRule]]:
        """Find a rule class in a module by rule_id."""
        # Check for a direct mapping
        rule_map = getattr(module, '_RULE_MAP', None)
        if rule_map and rule_id in rule_map:
            return rule_map[rule_id]
        
        # Search through module attributes
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, BaseRule)
                and hasattr(attr, 'rule_id')
                and attr.rule_id == rule_id
            ):
                return attr
        
        return None
    
    def get_all_rules(self) -> Dict[str, Type[BaseRule]]:
        """Get all available rule classes (loads them all)."""
        all_rules = {}
        for rule_id in self._rule_modules:
            rule_class = self.get_rule(rule_id)
            if rule_class:
                all_rules[rule_id] = rule_class
        return all_rules
    
    def list_available_rules(self) -> List[str]:
        """List all available rule IDs without loading them."""
        return list(self._rule_modules.keys())
    
    def register_rule(self, rule_id: str, rule_class: Type[BaseRule]) -> None:
        """Manually register a rule class."""
        self._rule_cache[rule_id] = rule_class
    
    def register_rule_module(self, rule_id: str, module_path: str) -> None:
        """Register a rule ID to module mapping."""
        self._rule_modules[rule_id] = module_path


# Global lazy registry instance
_lazy_registry: Optional[LazyRuleRegistry] = None


def get_lazy_registry() -> LazyRuleRegistry:
    """Get the global lazy rule registry."""
    global _lazy_registry
    if _lazy_registry is None:
        _lazy_registry = LazyRuleRegistry()
    return _lazy_registry


# Backward compatibility functions
def get_all_rules() -> Dict[str, Type[BaseRule]]:
    """Get all rule classes (loads them all)."""
    return get_lazy_registry().get_all_rules()


def get_rule(rule_id: str) -> Optional[Type[BaseRule]]:
    """Get a rule class by ID."""
    return get_lazy_registry().get_rule(rule_id)


def register(rule_class: Type[BaseRule]) -> Type[BaseRule]:
    """Decorator to register a rule class."""
    if hasattr(rule_class, 'rule_id'):
        get_lazy_registry().register_rule(rule_class.rule_id, rule_class)
    return rule_class


# Initialize the registry with built-in rules
def _initialize_built_in_rules():
    """Initialize built-in rule mappings."""
    registry = get_lazy_registry()
    
    # Add rule mappings for modules that have multiple rules
    registry.register_rule_module("ruff-duplicate-imports", "pprefact.rules.ruff_based")
    registry.register_rule_module("ruff-wildcard-imports", "pprefact.rules.ruff_based")
    registry.register_rule_module("ruff-print-statements", "pprefact.rules.ruff_based")
    registry.register_rule_module("ruff-sorted-imports", "pprefact.rules.ruff_based")
    
    registry.register_rule_module("mypy-type-checking", "pprefact.rules.mypy_based")
    registry.register_rule_module("smart-return-type", "pprefact.rules.mypy_based")
    
    registry.register_rule_module("import-section-separators", "pprefact.rules.isort_based")
    registry.register_rule_module("custom-import-organization", "pprefact.rules.isort_based")
    
    registry.register_rule_module("autoflake-unused-variables", "pprefact.rules.autoflake_based")
    registry.register_rule_module("autoflake-duplicate-keys", "pprefact.rules.autoflake_based")
    registry.register_rule_module("autoflake-all", "pprefact.rules.autoflake_based")
    
    registry.register_rule_module("flynt-string-formatting", "pprefact.rules.string_transformations")
    registry.register_rule_module("context-aware-string-concat", "pprefact.rules.string_transformations")
    
    registry.register_rule_module("pylint-string-concat", "pprefact.rules.pylint_based")
    registry.register_rule_module("pylint-comprehensive", "pprefact.rules.pylint_based")
    
    registry.register_rule_module("unimport-duplicate-imports", "pprefact.rules.unimport_based")
    registry.register_rule_module("unimport-star-imports", "pprefact.rules.unimport_based")
    registry.register_rule_module("unimport-all", "pprefact.rules.unimport_based")
    
    registry.register_rule_module("importchecker-duplicate-imports", "pprefact.rules.importchecker_based")
    registry.register_rule_module("import-dependency-analysis", "pprefact.rules.importchecker_based")
    registry.register_rule_module("import-optimizer", "pprefact.rules.importchecker_based")
    
    registry.register_rule_module("import-linter-no-relative", "pprefact.rules.import_linter_based")
    registry.register_rule_module("import-linter-independence", "pprefact.rules.import_linter_based")
    registry.register_rule_module("import-linter-custom-architecture", "pprefact.rules.import_linter_based")
    
    registry.register_rule_module("composite-imports", "pprefact.rules.composite")
    registry.register_rule_module("composite-type-checking", "pprefact.rules.composite")
    
    # LLM-specific rules
    registry.register_rule_module("llm-hallucinations", "pprefact.rules.llm_specific")
    registry.register_rule_module("magic-numbers", "pprefact.rules.llm_specific")
    registry.register_rule_module("llm-generated-code", "pprefact.rules.llm_specific")
    registry.register_rule_module("ai-boilerplate", "pprefact.rules.llm_specific")


# Initialize built-in rules
_initialize_built_in_rules()
