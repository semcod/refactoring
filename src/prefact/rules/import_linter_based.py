"""Import-linter integration for advanced import architecture rules.

This module provides integration with import-linter for enforcing
architectural constraints on imports, including layering rules and
relative import restrictions.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import yaml
from pathlib import Path
from typing import Dict, List, Optional

from prefact.config import Config
from prefact.models import Fix, Issue, Severity, ValidationResult
from prefact.rules import BaseRule, register


class ImportLinterHelper:
    """Helper class for import-linter operations."""
    
    @staticmethod
    def create_config(config: Dict, output_path: Path) -> None:
        """Create an import-linter configuration file."""
        linter_config = {
            "root_package": config.get("root_package", "planfile"),
            "include": config.get("include", "src"),
        }
        
        # Add layers if specified
        if "layers" in config:
            linter_config["layers"] = config["layers"]
        
        # Add dependencies if specified
        if "dependencies" in config:
            linter_config["dependencies"] = config["dependencies"]
        
        # Add independence rules if specified
        if "independence" in config:
            linter_config["independence"] = config["independence"]
        
        # Add forbidden rules if specified
        if "forbidden" in config:
            linter_config["forbidden"] = config["forbidden"]
        
        with open(output_path, "w") as f:
            yaml.dump(linter_config, f, default_flow_style=False)
    
    @staticmethod
    def run_linter(config_path: Path) -> List[Dict]:
        """Run import-linter and return results."""
        cmd = ["import-linter", "run", str(config_path)]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            # Parse output
            issues = []
            if result.returncode != 0:  # Violations found
                lines = result.stdout.splitlines()
                for line in lines:
                    if " - " in line:
                        # Parse violation
                        parts = line.split(" - ", 1)
                        if len(parts) == 2:
                            file_part = parts[0]
                            message = parts[1]
                            
                            # Extract file and line
                            if ":" in file_part:
                                file_path, line_num = file_part.rsplit(":", 1)
                                try:
                                    line_num = int(line_num)
                                except ValueError:
                                    line_num = 1
                            else:
                                file_path = file_part
                                line_num = 1
                            
                            issues.append({
                                "file": file_path,
                                "line": line_num,
                                "message": message,
                                "type": "violation"
                            })
            
            return issues
        except (subprocess.SubprocessError, FileNotFoundError):
            return []
    
    @staticmethod
    def check_file(file_path: Path, config: Dict) -> List[Dict]:
        """Check a specific file using import-linter."""
        # Create temporary config
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as tmp:
            config_path = Path(tmp.name)
        
        try:
            ImportLinterHelper.create_config(config, config_path)
            all_issues = ImportLinterHelper.run_linter(config_path)
            
            # Filter issues for the specific file
            return [
                issue for issue in all_issues
                if Path(issue.get("file", "")).resolve() == file_path.resolve()
            ]
        finally:
            config_path.unlink(missing_ok=True)


@register
class ImportLinterLayers(BaseRule):
    """Enforce import layering rules using import-linter."""
    
    rule_id = "import-layers"
    description = "Enforce import layering using import-linter"
    
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.linter_config = self._load_linter_config()
    
    def _load_linter_config(self) -> Dict:
        """Load import-linter configuration."""
        return {
            "root_package": self.config.package_name or "planfile",
            "layers": self.config.get_rule_option(
                self.rule_id, "layers", [
                    {"name": "domain", "modules": ["planfile.domain.*"]},
                    {"name": "service", "modules": ["planfile.service.*"]},
                    {"name": "api", "modules": ["planfile.api.*"]},
                ]
            ),
            "dependencies": self.config.get_rule_option(
                self.rule_id, "dependencies", [
                    {"layers": ["api"], "may_depend_on": ["service"]},
                    {"layers": ["service"], "may_depend_on": ["domain"]},
                ]
            )
        }
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        issues = []
        results = ImportLinterHelper.check_file(path, self.linter_config)
        
        for item in results:
            issues.append(Issue(
                rule_id=self.rule_id,
                file=path,
                line=item.get("line", 1),
                col=0,
                message=item.get("message", "Layer violation"),
                severity=Severity.ERROR,
                original="layer violation"
            ))
        
        return issues
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        # Layer violations require architectural changes
        # We can only report them, not fix automatically
        return source, []
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        # Re-check for layer violations
        results = ImportLinterHelper.check_file(path, self.linter_config)
        
        return ValidationResult(
            file=path,
            passed=len(results) == 0,
            checks=["no_layer_violations"] if not results else [],
            errors=[f"Still has {len(results)} layer violations"] if results else []
        )


@register
class ImportLinterNoRelative(BaseRule):
    """Block relative imports using import-linter."""
    
    rule_id = "no-relative-imports"
    description = "Block relative imports using import-linter"
    
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.linter_config = self._load_linter_config()
    
    def _load_linter_config(self) -> Dict:
        """Load configuration to block relative imports."""
        return {
            "root_package": self.config.package_name or "planfile",
            "forbidden": self.config.get_rule_option(
                self.rule_id, "forbidden", [
                    {
                        "type": "relative_imports",
                        "from_modules": ["planfile.*"],
                        "message": "Relative imports are not allowed"
                    }
                ]
            )
        }
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        issues = []
        
        # First, quick AST check for relative imports
        import ast
        try:
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.level > 0:
                    # Found relative import
                    issues.append(Issue(
                        rule_id=self.rule_id,
                        file=path,
                        line=node.lineno,
                        col=node.col_offset,
                        message=f"Relative import not allowed (level={node.level})",
                        severity=Severity.ERROR,
                        original="relative import"
                    ))
        except SyntaxError:
            pass
        
        # Then use import-linter for more comprehensive checking
        results = ImportLinterHelper.check_file(path, self.linter_config)
        for item in results:
            if "relative" in item.get("message", "").lower():
                issues.append(Issue(
                    rule_id=self.rule_id,
                    file=path,
                    line=item.get("line", 1),
                    col=0,
                    message=item.get("message", "Relative import not allowed"),
                    severity=Severity.ERROR,
                    original="relative import"
                ))
        
        return issues
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        # Delegate to relative imports fixer
        from prefact.rules.relative_imports import RelativeToAbsoluteImports
        fixer = RelativeToAbsoluteImports(self.config)
        return fixer.fix(path, source, issues)
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        # Check if relative imports remain
        results = ImportLinterHelper.check_file(path, self.linter_config)
        
        return ValidationResult(
            file=path,
            passed=len(results) == 0,
            checks=["no_relative_imports"] if not results else [],
            errors=[f"Still has {len(results)} relative imports"] if results else []
        )


@register
class ImportLinterIndependence(BaseRule):
    """Ensure module independence using import-linter."""
    
    rule_id = "module-independence"
    description = "Ensure modules remain independent"
    
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.linter_config = self._load_linter_config()
    
    def _load_linter_config(self) -> Dict:
        """Load independence configuration."""
        return {
            "root_package": self.config.package_name or "planfile",
            "independence": self.config.get_rule_option(
                self.rule_id, "independence", [
                    {"modules": ["planfile.domain.*"]},
                    {"modules": ["planfile.utils.*"]},
                ]
            )
        }
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        issues = []
        results = ImportLinterHelper.check_file(path, self.linter_config)
        
        for item in results:
            issues.append(Issue(
                rule_id=self.rule_id,
                file=path,
                line=item.get("line", 1),
                col=0,
                message=item.get("message", "Independence violation"),
                severity=Severity.WARNING,
                original="independence violation"
            ))
        
        return issues
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        # Independence violations require architectural changes
        return source, []
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        results = ImportLinterHelper.check_file(path, self.linter_config)
        
        return ValidationResult(
            file=path,
            passed=len(results) == 0,
            checks=["independence_maintained"] if not results else [],
            errors=[f"Still has {len(results)} independence violations"] if results else []
        )


# Advanced: Custom architectural rules
@register
class ImportLinterCustomArchitecture(BaseRule):
    """Enforce custom architectural rules using import-linter."""
    
    rule_id = "custom-architecture"
    description = "Enforce custom architectural import rules"
    
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.linter_config = self._load_custom_config()
    
    def _load_custom_config(self) -> Dict:
        """Load custom architectural configuration."""
        custom_rules = self.config.get_rule_option(self.rule_id, "rules", {})
        
        config = {
            "root_package": self.config.package_name or "planfile"
        }
        
        # Add custom layers
        if "layers" in custom_rules:
            config["layers"] = custom_rules["layers"]
        
        # Add custom dependencies
        if "dependencies" in custom_rules:
            config["dependencies"] = custom_rules["dependencies"]
        
        # Add forbidden patterns
        if "forbidden" in custom_rules:
            config["forbidden"] = custom_rules["forbidden"]
        
        # Add independence rules
        if "independence" in custom_rules:
            config["independence"] = custom_rules["independence"]
        
        return config
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        issues = []
        results = ImportLinterHelper.check_file(path, self.linter_config)
        
        for item in results:
            # Determine severity based on rule type
            message = item.get("message", "").lower()
            if "forbidden" in message:
                severity = Severity.ERROR
            elif "violation" in message:
                severity = Severity.WARNING
            else:
                severity = Severity.INFO
            
            issues.append(Issue(
                rule_id=self.rule_id,
                file=path,
                line=item.get("line", 1),
                col=0,
                message=item.get("message", "Architecture rule violation"),
                severity=severity,
                original="architecture violation"
            ))
        
        return issues
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        # Most architectural rules require manual fixes
        # We can only fix simple cases like relative imports
        relative_issues = [i for i in issues if "relative" in i.message.lower()]
        if relative_issues:
            from prefact.rules.relative_imports import RelativeToAbsoluteImports
            fixer = RelativeToAbsoluteImports(self.config)
            return fixer.fix(path, source, relative_issues)
        
        return source, []
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        results = ImportLinterHelper.check_file(path, self.linter_config)
        
        return ValidationResult(
            file=path,
            passed=len(results) == 0,
            checks=["architecture_rules_satisfied"] if not results else [],
            errors=[f"Still has {len(results)} architecture violations"] if results else []
        )


# Configuration generator for import-linter
def generate_import_linter_config(config: Config, output_path: Path) -> None:
    """Generate a comprehensive import-linter configuration."""
    linter_config = {
        "root_package": config.package_name or "planfile",
        "include": "src",
        "layers": [
            {"name": "domain", "modules": ["planfile.domain.*"]},
            {"name": "service", "modules": ["planfile.service.*"]},
            {"name": "api", "modules": ["planfile.api.*"]},
            {"name": "cli", "modules": ["planfile.cli.*"]},
        ],
        "dependencies": [
            {"layers": ["api"], "may_depend_on": ["service", "domain"]},
            {"layers": ["service"], "may_depend_on": ["domain"]},
            {"layers": ["cli"], "may_depend_on": ["service", "domain"]},
        ],
        "forbidden": [
            {
                "type": "relative_imports",
                "from_modules": ["planfile.*"],
                "message": "Use absolute imports instead of relative imports"
            }
        ],
        "independence": [
            {"modules": ["planfile.domain.*"]},
            {"modules": ["planfile.utils.*"]},
        ]
    }
    
    # Add custom rules from config
    custom_arch = config.get_rule_option("custom-architecture", "rules", {})
    if custom_arch:
        if "layers" in custom_arch:
            linter_config["layers"].extend(custom_arch["layers"])
        if "dependencies" in custom_arch:
            linter_config["dependencies"].extend(custom_arch["dependencies"])
        if "forbidden" in custom_arch:
            linter_config["forbidden"].extend(custom_arch["forbidden"])
        if "independence" in custom_arch:
            linter_config["independence"].extend(custom_arch["independence"])
    
    with open(output_path, "w") as f:
        yaml.dump(linter_config, f, default_flow_style=False)
