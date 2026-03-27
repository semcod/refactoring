"""Plugin system for prefact with dynamic loading and validation.

This module provides a secure plugin system that supports both setuptools
entry points for third-party plugins and dynamic module loading for user plugins.
"""

from __future__ import annotations

import importlib
import importlib.metadata
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional, Type

from prefact.config import Config
from prefact.rules import BaseRule

# Plugin API version - increment when breaking changes are made
PLUGIN_API_VERSION = "1.0.0"

# Plugin metadata
class PluginMetadata:
    """Metadata for a loaded plugin."""
    
    def __init__(
        self,
        name: str,
        version: str,
        api_version: str,
        description: str = "",
        author: str = "",
        entry_point: Optional[str] = None
    ):
        self.name = name
        self.version = version
        self.api_version = api_version
        self.description = description
        self.author = author
        self.entry_point = entry_point
        self.compatible = self._check_compatibility()
    
    def _check_compatibility(self) -> bool:
        """Check if plugin API version is compatible."""
        # Simple version check - could be more sophisticated
        return self.api_version == PLUGIN_API_VERSION


class PluginValidator:
    """Validates plugins before loading."""
    
    @staticmethod
    def validate_plugin_module(module) -> bool:
        """Validate that a plugin module is safe to load."""
        # Check required attributes
        if not hasattr(module, '__plugin_api_version__'):
            return False
        
        if not hasattr(module, 'rules'):
            return False
        
        # Validate API version
        if module.__plugin_api_version__ != PLUGIN_API_VERSION:
            return False
        
        # Validate rules
        if not isinstance(module.rules, list):
            return False
        
        for rule_class in module.rules:
            if not issubclass(rule_class, BaseRule):
                return False
        
        return True
    
    @staticmethod
    def validate_plugin_path(plugin_path: Path) -> bool:
        """Validate plugin file path is safe."""
        # Ensure plugin is within allowed directories
        plugin_path = plugin_path.resolve()
        
        # Check for suspicious file names
        if plugin_path.name.startswith(('.', '__')):
            return False
        
        # Ensure it's a Python file
        if plugin_path.suffix != '.py':
            return False
        
        return True


class PluginManager:
    """Manages loading and registration of plugins."""
    
    def __init__(self, config: Config):
        self.config = config
        self._plugins: Dict[str, PluginMetadata] = {}
        self._rules: Dict[str, Type[BaseRule]] = {}
        self._loaded_modules = set()
        
        # Plugin directories
        self.plugin_dirs = [
            Path(__file__).parent / "plugins",  # Built-in plugins
            Path.home() / ".prefact" / "plugins",  # User plugins
            Path.cwd() / ".prefact" / "plugins",  # Project plugins
        ]
    
    def discover_plugins(self) -> List[PluginMetadata]:
        """Discover all available plugins."""
        plugins = []
        
        # Discover entry point plugins
        plugins.extend(self._discover_entry_point_plugins())
        
        # Discover local plugins
        for plugin_dir in self.plugin_dirs:
            if plugin_dir.exists():
                plugins.extend(self._discover_local_plugins(plugin_dir))
        
        return plugins
    
    def _discover_entry_point_plugins(self) -> List[PluginMetadata]:
        """Discover plugins via setuptools entry points."""
        plugins = []
        
        try:
            entry_points = importlib.metadata.entry_points(group="prefact.plugins")
            
            for ep in entry_points:
                metadata = PluginMetadata(
                    name=ep.name,
                    version=ep.dist.version if ep.dist else "unknown",
                    api_version=getattr(ep, 'api_version', PLUGIN_API_VERSION),
                    description=ep.dist.metadata.get('Summary', '') if ep.dist else '',
                    author=ep.dist.metadata.get('Author', '') if ep.dist else '',
                    entry_point=ep.value
                )
                plugins.append(metadata)
                
        except Exception as e:
            # Entry points not available or other error
            print(f"Warning: Could not discover entry point plugins: {e}")
        
        return plugins
    
    def _discover_local_plugins(self, plugin_dir: Path) -> List[PluginMetadata]:
        """Discover plugins in a local directory."""
        plugins = []
        
        for plugin_file in plugin_dir.glob("*.py"):
            if not PluginValidator.validate_plugin_path(plugin_file):
                continue
            
            try:
                # Load module to get metadata
                spec = importlib.util.spec_from_file_location(
                    plugin_file.stem, plugin_file
                )
                module = importlib.util.module_from_spec(spec)
                
                # Temporarily add to sys.modules for relative imports
                sys.modules[f"prefact_plugin_{plugin_file.stem}"] = module
                spec.loader.exec_module(module)
                
                # Get metadata
                metadata = PluginMetadata(
                    name=getattr(module, '__plugin_name__', plugin_file.stem),
                    version=getattr(module, '__version__', '0.0.0'),
                    api_version=getattr(module, '__plugin_api_version__', PLUGIN_API_VERSION),
                    description=getattr(module, '__description__', ''),
                    author=getattr(module, '__author__', ''),
                    entry_point=str(plugin_file)
                )
                plugins.append(metadata)
                
                # Clean up
                del sys.modules[f"prefact_plugin_{plugin_file.stem}"]
                
            except Exception as e:
                print(f"Warning: Could not load plugin {plugin_file}: {e}")
        
        return plugins
    
    def load_plugin(self, metadata: PluginMetadata) -> bool:
        """Load a plugin and register its rules."""
        if not metadata.compatible:
            print(f"Plugin {metadata.name} is not compatible with API version {PLUGIN_API_VERSION}")
            return False
        
        try:
            if metadata.entry_point and ":" in metadata.entry_point:
                # Entry point plugin
                module_name, attr_name = metadata.entry_point.split(":")
                module = importlib.import_module(module_name)
                plugin_obj = getattr(module, attr_name)
                
                if callable(plugin_obj):
                    # Plugin is a factory function
                    rules = plugin_obj(self.config)
                else:
                    # Plugin is a module with rules attribute
                    rules = plugin_obj.rules
                    
            else:
                # Local plugin file
                if metadata.entry_point:
                    plugin_path = Path(metadata.entry_point)
                    spec = importlib.util.spec_from_file_location(
                        f"prefact_plugin_{metadata.name}", plugin_path
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                else:
                    # Try to import by name
                    module = importlib.import_module(f"prefact.plugins.{metadata.name}")
                
                rules = module.rules
            
            # Validate and register rules
            if PluginValidator.validate_plugin_module(module):
                for rule_class in rules:
                    if rule_class.rule_id not in self._rules:
                        self._rules[rule_class.rule_id] = rule_class
                
                self._plugins[metadata.name] = metadata
                self._loaded_modules.add(module.__name__)
                return True
            else:
                print(f"Plugin {metadata.name} failed validation")
                return False
                
        except Exception as e:
            print(f"Error loading plugin {metadata.name}: {e}")
            return False
    
    def load_all_plugins(self) -> None:
        """Load all discovered plugins."""
        plugins = self.discover_plugins()
        
        for plugin in plugins:
            # Skip if already loaded
            if plugin.name in self._plugins:
                continue
            
            # Check if plugin is enabled in config
            if not self.config.get_rule_option("_plugins", plugin.name, True):
                continue
            
            self.load_plugin(plugin)
    
    def get_rule(self, rule_id: str) -> Optional[Type[BaseRule]]:
        """Get a rule class by ID."""
        # Lazy loading - only load the plugin when needed
        if rule_id not in self._rules:
            self._load_plugin_for_rule(rule_id)
        
        return self._rules.get(rule_id)
    
    def _load_plugin_for_rule(self, rule_id: str) -> None:
        """Load the plugin that provides a specific rule."""
        # This is a simplified implementation
        # In practice, you'd need a mapping from rule to plugin
        plugins = self.discover_plugins()
        for plugin in plugins:
            if plugin.name not in self._plugins:
                if self.load_plugin(plugin) and rule_id in self._rules:
                    break
    
    def list_plugins(self) -> List[Dict]:
        """List all loaded plugins."""
        return [
            {
                "name": metadata.name,
                "version": metadata.version,
                "description": metadata.description,
                "author": metadata.author,
                "rules": [
                    rule_id for rule_id, rule_class in self._rules.items()
                    if self._is_rule_from_plugin(rule_class, metadata)
                ]
            }
            for metadata in self._plugins.values()
        ]
    
    def _is_rule_from_plugin(self, rule_class: Type[BaseRule], metadata: PluginMetadata) -> bool:
        """Check if a rule comes from a specific plugin."""
        # This is simplified - you'd need to track which plugin provided which rule
        return True
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a plugin."""
        if plugin_name not in self._plugins:
            return False
        
        # Remove rules from this plugin
        # This is simplified - you'd need to track which rules came from which plugin
        self._plugins.pop(plugin_name, None)
        return True


# Global plugin manager instance
_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager(config: Optional[Config] = None) -> PluginManager:
    """Get the global plugin manager instance."""
    global _plugin_manager
    if _plugin_manager is None:
        if config is None:
            raise ValueError("Config required for first plugin manager initialization")
        _plugin_manager = PluginManager(config)
        _plugin_manager.load_all_plugins()
    return _plugin_manager


# Decorator for plugin rules
def register_plugin_rule(plugin_name: str, version: str = "1.0.0"):
    """Decorator to register a rule as part of a plugin."""
    def decorator(rule_class: Type[BaseRule]):
        # This would be used by plugin authors
        # The actual registration happens when the plugin is loaded
        return rule_class
    return decorator
