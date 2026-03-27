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
        rules = {}
        for rule_id, rule_raw in raw.pop("rules", {}).items():
            if isinstance(rule_raw, bool):
                rules[rule_id] = RuleConfig(enabled=rule_raw)
            elif isinstance(rule_raw, dict):
                rules[rule_id] = RuleConfig(**rule_raw)
        defaults_include = ["**/*.py"]
        defaults_exclude = [
            "**/__pycache__/**", "**/node_modules/**", "**/.venv/**",
            "**/venv/**", "**/.git/**", "**/build/**", "**/dist/**", "**/*.egg-info/**",
        ]
        return cls(
            project_root=Path(raw.pop("project_root", Path.cwd())),
            package_name=raw.pop("package_name", ""),
            include=raw.pop("include", defaults_include),
            exclude=raw.pop("exclude", defaults_exclude),
            rules=rules,
            **{k: v for k, v in raw.items() if k in cls.__dataclass_fields__},
        )

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

        pyproject = self.project_root / "pyproject.toml"
        if pyproject.exists():
            try:
                import tomllib
            except ModuleNotFoundError:
                try:
                    import tomli as tomllib  # type: ignore[no-redef]
                except ModuleNotFoundError:
                    tomllib = None  # type: ignore[assignment]
            if tomllib is not None:
                try:
                    data = tomllib.loads(pyproject.read_text())
                    name = data.get("project", {}).get("name", "")
                    if name:
                        self.package_name = name.replace("-", "_")
                        return self.package_name
                except Exception:
                    pass

        # Fallback: look for src/<pkg>/__init__.py
        src = self.project_root / "src"
        if src.is_dir():
            for child in src.iterdir():
                if child.is_dir() and (child / "__init__.py").exists():
                    self.package_name = child.name
                    return self.package_name

        # Fallback: top-level package directory
        for child in self.project_root.iterdir():
            if (
                child.is_dir()
                and (child / "__init__.py").exists()
                and child.name not in ("tests", "test", "docs", "scripts")
            ):
                self.package_name = child.name
                return self.package_name

        return ""
