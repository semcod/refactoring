"""Extended YAML configuration parser for prefact.

This module provides advanced configuration parsing with support for:
- Tool-specific configurations
- Composite rules
- Performance settings
- Plugin configurations
- Environment-specific overrides
"""


import os
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional

# Constants for configuration
DEFAULT_CACHE_SIZE = 104857600  # 100MB
DEFAULT_MAX_LINE_LENGTH = 88

from prefact.config import Config, RuleConfig


class ExtendedConfig(Config):
    """Extended configuration with additional features."""
    
    def __init__(
        self,
        project_root: Optional[Path] = None,
        package_name: str = "",
        include: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None,
        rules: Optional[Dict[str, Any]] = None,
        tools: Optional[Dict[str, Any]] = None,
        performance: Optional[Dict[str, Any]] = None,
        plugins: Optional[Dict[str, Any]] = None,
        environments: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        super().__init__(project_root, package_name, include, exclude, rules)
        
        # Tool configurations
        self.tools: Dict[str, Any] = tools or {}
        
        # Performance settings
        self.performance: Dict[str, Any] = performance or {}
        
        # Plugin configurations
        self.plugins: Dict[str, Any] = plugins or {}
        
        # Environment-specific configurations
        self.environments: Dict[str, Any] = environments or {}
        
        # Additional settings
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    @classmethod
    def from_yaml(cls, path: Path, environment: Optional[str] = None) -> "ExtendedConfig":
        """Load configuration from YAML file with environment support."""
        if not path.exists():
            return cls(project_root=Path.cwd())
        
        with open(path) as f:
            raw = yaml.safe_load(f) or {}
        
        # Apply environment overrides
        if environment and "environments" in raw:
            env_config = raw["environments"].get(environment, {})
            # Merge environment config
            raw = cls._deep_merge(raw, env_config)
        
        # Parse rules
        rules = {}
        for rule_id, rule_raw in raw.pop("rules", {}).items():
            if isinstance(rule_raw, bool):
                rules[rule_id] = RuleConfig(enabled=rule_raw)
            elif isinstance(rule_raw, dict):
                # Filter out extended fields that RuleConfig doesn't support
                basic_fields = {
                    k: v for k, v in rule_raw.items() 
                    if k in ['enabled', 'severity', 'options']
                }
                rules[rule_id] = RuleConfig(**basic_fields)
                
                # Store extended fields separately
                if hasattr(rules[rule_id], '_extended'):
                    rules[rule_id]._extended.update(rule_raw)
                else:
                    rules[rule_id]._extended = {
                        k: v for k, v in rule_raw.items()
                        if k not in ['enabled', 'severity', 'options']
                    }
        
        # Extract tool configurations
        tools = raw.pop("tools", {})
        
        # Extract performance settings
        performance = raw.pop("performance", {})
        
        # Extract plugin configurations
        plugins = raw.pop("plugins", {})
        
        # Extract environments (for reference)
        environments = raw.pop("environments", {})
        
        # Set defaults
        defaults_include = raw.pop("include", ["**/*.py"])
        defaults_exclude = raw.pop("exclude", [
            "**/__pycache__/**",
            "**/node_modules/**",
            "**/.venv/**",
            "**/venv/**",
            "**/.git/**",
            "**/build/**",
            "**/dist/**",
            "**/*.egg-info/**",
        ])
        
        return cls(
            project_root=Path(raw.pop("project_root", Path.cwd())),
            package_name=raw.pop("package_name", ""),
            include=raw.pop("include", defaults_include),
            exclude=raw.pop("exclude", defaults_exclude),
            rules=rules,
            tools=tools,
            performance=performance,
            plugins=plugins,
            environments=environments,
            **{k: v for k, v in raw.items() if k in cls.__dataclass_fields__}
        )
    
    @staticmethod
    def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ExtendedConfig._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def get_tool_config(self, tool_name: str) -> Dict[str, Any]:
        """Get configuration for a specific tool."""
        return self.tools.get(tool_name, {})
    
    def get_performance_setting(self, key: str, default: Any = None) -> Any:
        """Get a performance setting."""
        return self.performance.get(key, default)
    
    def get_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """Get configuration for a specific plugin."""
        return self.plugins.get(plugin_name, {})
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        result = super().to_dict()
        
        result.update({
            "tools": self.tools,
            "performance": self.performance,
            "plugins": self.plugins,
            "environments": self.environments,
        })
        
        return result


class ConfigValidator:
    """Validate configuration files."""
    
    @staticmethod
    def validate(config: ExtendedConfig) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        # Validate tool configurations
        for tool_name, tool_config in config.tools.items():
            if tool_name == "ruff":
                errors.extend(ConfigValidator._validate_ruff_config(tool_config))
            elif tool_name == "mypy":
                errors.extend(ConfigValidator._validate_mypy_config(tool_config))
            elif tool_name == "isort":
                errors.extend(ConfigValidator._validate_isort_config(tool_config))
        
        # Validate performance settings
        errors.extend(ConfigValidator._validate_performance_config(config.performance))
        
        # Validate rule configurations
        for rule_id, rule_config in config.rules.items():
            errors.extend(ConfigValidator._validate_rule_config(rule_id, rule_config))
        
        return errors
    
    @staticmethod
    def _validate_ruff_config(config: Dict[str, Any]) -> List[str]:
        """Validate Ruff configuration."""
        errors = []
        
        if "max_line_length" in config:
            if not isinstance(config["max_line_length"], int) or config["max_line_length"] <= 0:
                errors.append("ruff.max_line_length must be a positive integer")
        
        if "select" in config:
            if not isinstance(config["select"], list):
                errors.append("ruff.select must be a list")
        
        return errors
    
    @staticmethod
    def _validate_mypy_config(config: Dict[str, Any]) -> List[str]:
        """Validate MyPy configuration."""
        errors = []
        
        if "strict" in config:
            if not isinstance(config["strict"], bool):
                errors.append("mypy.strict must be a boolean")
        
        return errors
    
    @staticmethod
    def _validate_isort_config(config: Dict[str, Any]) -> List[str]:
        """Validate ISort configuration."""
        errors = []
        
        if "profile" in config:
            valid_profiles = ["black", "django", "pycharm", "google"]
            if config["profile"] not in valid_profiles:
                errors.append(f"isort.profile must be one of {valid_profiles}")
        
        return errors
    
    @staticmethod
    def _validate_performance_config(config: Dict[str, Any]) -> List[str]:
        """Validate performance configuration."""
        errors = []
        
        if "max_workers" in config:
            if not isinstance(config["max_workers"], int) or config["max_workers"] <= 0:
                errors.append("performance.max_workers must be a positive integer")
        
        if "cache_size" in config:
            if not isinstance(config["cache_size"], int) or config["cache_size"] <= 0:
                errors.append("performance.cache_size must be a positive integer")
        
        return errors
    
    @staticmethod
    def _validate_rule_config(rule_id: str, config: RuleConfig) -> List[str]:
        """Validate individual rule configuration."""
        errors = []
        
        # Rule-specific validation
        if rule_id == "magic-numbers":
            if "allowed_numbers" in config.options:
                allowed = config.options["allowed_numbers"]
                if not isinstance(allowed, list) or not all(isinstance(n, (int, float)) for n in allowed):
                    errors.append(f"{rule_id}.allowed_numbers must be a list of numbers")
        
        elif rule_id == "llm-hallucinations":
            if "patterns" in config.options:
                patterns = config.options["patterns"]
                if not isinstance(patterns, list):
                    errors.append(f"{rule_id}.patterns must be a list")
        
        return errors


class ConfigGenerator:
    """Generate configuration files."""
    
    @staticmethod
    def generate_extended_config(
        project_root: Path,
        tools: Optional[List[str]] = None,
        rules: Optional[List[str]] = None
    ) -> str:
        """Generate an extended prefact.yaml configuration."""
        if tools is None:
            tools = ["ruff", "mypy", "isort"]
        
        if rules is None:
            rules = ["unused-imports", "relative-imports", "missing-return-type"]
        
        config = {
            "project_root": str(project_root),
            "package_name": project_root.name,
            "include": ["**/*.py"],
            "exclude": [
                "**/__pycache__/**",
                "**/node_modules/**",
                "**/.venv/**",
                "**/venv/**",
                "**/.git/**",
                "**/build/**",
                "**/dist/**",
                "**/*.egg-info/**",
                "**/tests/**",
            ],
            "tools": {
                "parallel": True,
                "cache": True,
            },
            "performance": {
                "max_workers": 4,
                "cache_size": DEFAULT_CACHE_SIZE,  # 100MB
                "chunk_size": 10,
            },
            "rules": {},
            "plugins": {
                "enabled": True,
                "directories": [
                    "~/.prefact/plugins",
                    "./.prefact/plugins",
                ],
            },
            "environments": {
                "development": {
                    "rules": {
                        "print-statements": {"enabled": True},
                        "magic-numbers": {"enabled": False},
                    },
                    "performance": {
                        "max_workers": 2,
                    },
                },
                "production": {
                    "rules": {
                        "print-statements": {"enabled": False},
                        "magic-numbers": {"enabled": True},
                    },
                    "performance": {
                        "max_workers": 8,
                    },
                },
            },
        }
        
        # Add tool-specific configurations
        if "ruff" in tools:
            config["tools"]["ruff"] = {
                "enabled": True,
                "max_line_length": DEFAULT_MAX_LINE_LENGTH,
                "select": ["E", "F", "W", "I"],
                "ignore": ["E501"],
            }
        
        if "mypy" in tools:
            config["tools"]["mypy"] = {
                "enabled": True,
                "strict": False,
                "ignore_missing_imports": True,
            }
        
        if "isort" in tools:
            config["tools"]["isort"] = {
                "enabled": True,
                "profile": "black",
                "multi_line_output": 3,
            }
        
        # Add rule configurations
        for rule_id in rules:
            if rule_id == "unused-imports":
                config["rules"][rule_id] = {
                    "enabled": True,
                    "tools": ["ruff", "autoflake"],
                    "severity": "error",
                }
            elif rule_id == "relative-imports":
                config["rules"][rule_id] = {
                    "enabled": True,
                    "tools": ["libcst"],
                    "auto_fix": True,
                }
            elif rule_id == "missing-return-type":
                config["rules"][rule_id] = {
                    "enabled": True,
                    "tools": ["mypy"],
                    "severity": "warning",
                }
            elif rule_id == "llm-hallucinations":
                config["rules"][rule_id] = {
                    "enabled": True,
                    "patterns": [
                        {"pattern": "TODO: implement", "severity": "warning"},
                        {"pattern": "placeholder", "severity": "error"},
                    ],
                }
            elif rule_id == "magic-numbers":
                config["rules"][rule_id] = {
                    "enabled": True,
                    "threshold": 10,
                    "allowed_numbers": [0, 1, -1, 2, 10, 100],
                }
        
        return yaml.dump(config, default_flow_style=False, sort_keys=False)
    
    @staticmethod
    def generate_composite_rule_config(
        name: str,
        description: str,
        tools: List[str],
        strategy: str = "parallel"
    ) -> Dict[str, Any]:
        """Generate configuration for a composite rule."""
        return {
            "id": f"composite-{name}",
            "description": description,
            "enabled": True,
            "tools": tools,
            "strategy": strategy,
            "tool_priorities": {tool: i for i, tool in enumerate(tools)},
        }
    
    @staticmethod
    def save_config(config: Dict[str, Any], output_path: Path) -> None:
        """Save configuration to YAML file."""
        with open(output_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)


# Utility functions
def load_config_with_env(
    config_path: Optional[Path] = None,
    environment: Optional[str] = None
) -> ExtendedConfig:
    """Load configuration with environment detection."""
    if config_path is None:
        # Look for prefact.yaml in common locations
        cwd = Path.cwd()
        for path in [cwd, cwd / ".prefact", cwd.parent]:
            config_file = path / "prefact.yaml"
            if config_file.exists():
                config_path = config_file
                break
    
    if config_path is None:
        return ExtendedConfig(project_root=Path.cwd())
    
    # Detect environment
    if environment is None:
        environment = os.getenv("PREFACT_ENV", "development")
    
    return ExtendedConfig.from_yaml(config_path, environment)


def merge_configs(base: ExtendedConfig, override: ExtendedConfig) -> ExtendedConfig:
    """Merge two configurations."""
    merged_dict = ExtendedConfig._deep_merge(base.to_dict(), override.to_dict())
    
    return ExtendedConfig(
        project_root=Path(merged_dict["project_root"]),
        package_name=merged_dict["package_name"],
        include=merged_dict["include"],
        exclude=merged_dict["exclude"],
        rules=merged_dict["rules"],
        tools=merged_dict["tools"],
        performance=merged_dict["performance"],
        plugins=merged_dict["plugins"],
        environments=merged_dict["environments"],
    )
