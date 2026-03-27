"""Configuration management for prefact."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class RuleConfig:
    """Configuration for a single rule."""

    enabled: bool = True
    severity: str = "warning"
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class Config:
    """Top-level configuration."""

    # Project root (auto-detected or explicit)
    project_root: Path = field(default_factory=lambda: Path.cwd())

    # Package name used for absolute import resolution
    package_name: str = ""

    # File patterns to include / exclude
    include: list[str] = field(default_factory=lambda: ["**/*.py"])
    exclude: list[str] = field(
        default_factory=lambda: [
            "**/__pycache__/**",
            "**/node_modules/**",
            "**/.venv/**",
            "**/venv/**",
            "**/.git/**",
            "**/build/**",
            "**/dist/**",
            "**/*.egg-info/**",
        ]
    )

    # Rule-specific configuration
    rules: dict[str, RuleConfig] = field(default_factory=dict)

    # Pipeline flags
    dry_run: bool = False
    verbose: bool = False
    backup: bool = True

    # --- helpers --------------------------------------------------------

    @classmethod
    def from_yaml(cls, path: Path) -> "Config":
        """Load configuration from a YAML file."""
        raw = yaml.safe_load(path.read_text()) or {}
        
        # Extract and parse rules
        rules = cls._parse_rules(raw.pop("rules", {}))
        
        # Get default patterns
        defaults = cls._get_default_patterns()
        
        return cls(
            project_root=Path(raw.pop("project_root", Path.cwd())),
            package_name=raw.pop("package_name", ""),
            include=raw.pop("include", defaults["include"]),
            exclude=raw.pop("exclude", defaults["exclude"]),
            rules=rules,
            **{k: v for k, v in raw.items() if k in cls.__dataclass_fields__},
        )
    
    @classmethod
    def _parse_rules(cls, rules_raw: dict) -> dict[str, RuleConfig]:
        """Parse rules configuration from YAML."""
        rules = {}
        for rule_id, rule_raw in rules_raw.items():
            if isinstance(rule_raw, bool):
                rules[rule_id] = RuleConfig(enabled=rule_raw)
            elif isinstance(rule_raw, dict):
                rules[rule_id] = RuleConfig(**rule_raw)
        return rules
    
    @classmethod
    def _get_default_patterns(cls) -> dict[str, list[str]]:
        """Get default include/exclude patterns."""
        return {
            "include": ["**/*.py"],
            "exclude": [
                "**/__pycache__/**", "**/node_modules/**", "**/.venv/**",
                "**/venv/**", "**/.git/**", "**/build/**", "**/dist/**", "**/*.egg-info/**",
            ],
        }

    def rule_enabled(self, rule_id: str) -> bool:
        rc = self.rules.get(rule_id)
        return rc.enabled if rc else True
    
    def is_rule_enabled(self, rule_id: str) -> bool:
        """Alias for rule_enabled for compatibility."""
        return self.rule_enabled(rule_id)

    def rule_options(self, rule_id: str) -> dict[str, Any]:
        rc = self.rules.get(rule_id)
        return rc.options if rc else {}
    
    def get_rule_option(self, rule_id: str, option: str, default: Any = None) -> Any:
        """Get a specific option for a rule."""
        return self.rule_options(rule_id).get(option, default)
    
    def set_rule_option(self, rule_id: str, option: str, value: Any) -> None:
        """Set a specific option for a rule."""
        if rule_id not in self.rules:
            self.rules[rule_id] = RuleConfig()
        self.rules[rule_id].options[option] = value

    def detect_package_name(self) -> str:
        """Try to auto-detect the package name from pyproject.toml or project layout."""
        if self.package_name:
            return self.package_name

        # Try different detection strategies in order
        strategies = [
            self._detect_from_pyproject,
            self._detect_from_src_layout,
            self._detect_from_root_layout
        ]
        
        for strategy in strategies:
            name = strategy()
            if name:
                self.package_name = name
                return name
        
        return ""
    
    def _detect_from_pyproject(self) -> Optional[str]:
        """Detect package name from pyproject.toml."""
        pyproject = self.project_root / "pyproject.toml"
        if not pyproject.exists():
            return None
        
        # Try different TOML libraries
        tomllib = self._get_tomllib()
        if tomllib is None:
            return None
        
        try:
            data = tomllib.loads(pyproject.read_text())
            name = data.get("project", {}).get("name", "")
            if name:
                return name.replace("-", "_")
        except Exception:
            pass
        
        return None
    
    def _get_tomllib(self) -> Optional[Any]:
        """Get available TOML library."""
        try:
            import tomllib
            return tomllib
        except ModuleNotFoundError:
            try:
                import tomli as tomllib  # type: ignore[no-redef]
                return tomllib
            except ModuleNotFoundError:
                return None
    
    def _detect_from_src_layout(self) -> Optional[str]:
        """Detect package name from src/ layout."""
        src = self.project_root / "src"
        if not src.is_dir():
            return None
        
        for child in src.iterdir():
            if child.is_dir() and (child / "__init__.py").exists():
                return child.name
        
        return None
    
    def _detect_from_root_layout(self) -> Optional[str]:
        """Detect package name from root layout."""
        excluded_dirs = {"tests", "test", "docs", "scripts"}
        
        for child in self.project_root.iterdir():
            if (
                child.is_dir()
                and (child / "__init__.py").exists()
                and child.name not in excluded_dirs
            ):
                return child.name
        
        return None
