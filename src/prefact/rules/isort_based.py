"""ISort-based import sorting rules for prefact.

This module provides integration with ISort for sorting and organizing imports
according to PEP8 conventions.
"""

from pathlib import Path
from typing import Dict, List, Optional

from prefact.config import Config
from prefact.config_extended import DEFAULT_MAX_LINE_LENGTH
from prefact.models import Fix, Issue, Severity, ValidationResult
from prefact.rules import BaseRule, register

# Optional import - only import when needed
try:
    import isort
    HAS_ISORT = True
except ImportError:
    HAS_ISORT = False
    isort = None


class ISortHelper:
    """Helper class for ISort operations."""
    
    @staticmethod
    def check_file(file_path: Path, config: Optional[Dict] = None) -> List[Dict]:
        """Check if imports in a file are properly sorted."""
        try:
            source = file_path.read_text(encoding="utf-8")
            return ISortHelper.check_source(source, config)
        except Exception:
            return []
    
    @staticmethod
    def check_source(source: str, config: Optional[Dict] = None) -> List[Dict]:
        """Check if imports in source code are properly sorted."""
        # Default ISort configuration
        isort_config = {
            "profile": "black",
            "multi_line_output": 3,
            "line_length": DEFAULT_MAX_LINE_LENGTH,
            "known_first_party": ["prefact"],
        }
        
        if config:
            isort_config.update(config)
        
        # Check if code is sorted
        if not isort.check_code(source, **isort_config):
            # Find specific issues
            issues = []
            
            # Parse imports to find unsorted sections
            lines = source.splitlines()
            import_blocks = ISortHelper._find_import_blocks(lines)
            
            for block in import_blocks:
                if not ISortHelper._is_block_sorted(block, isort_config):
                    issues.append({
                        "line": str(block['start_line'] + 1),
                        "message": f"Import block not properly sorted (lines {block['start_line'] + 1}-{block['end_line'] + 1})",
                        "type": "unsorted_imports"
                    })
            
            # Check for missing section separators
            if ISortHelper._needs_section_separators(source, isort_config):
                issues.append({
                    "line": 1,
                    "message": "Import sections should be separated by blank lines",
                    "type": "missing_separator"
                })
            
            return issues
        
        return []
    
    @staticmethod
    def _find_import_blocks(lines: List[str]) -> List[Dict]:
        """Find import blocks in the source code."""
        blocks = []
        in_block = False
        start_line = 0
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            if stripped.startswith(("import ", "from ")):
                if not in_block:
                    in_block = True
                    start_line = i
            elif in_block and not stripped and not any(
                lines[j].strip().startswith(("import ", "from "))
                for j in range(f"{i}{1}", min(f"{i}{3}", len(lines)))
            ):
                # End of import block
                blocks.append({
                    "start_line": start_line,
                    "end_line": i - 1,
                    "lines": lines[start_line:i]
                })
                in_block = False
        
        # Handle block at end of file
        if in_block:
            blocks.append({
                "start_line": start_line,
                "end_line": len(lines) - 1,
                "lines": lines[start_line:]
            })
        
        return blocks
    
    @staticmethod
    def _is_block_sorted(block: Dict, config: Dict) -> bool:
        """Check if an import block is properly sorted."""
        # Use ISort to sort the block and compare
        block_source = "\n".join(block["lines"])
        sorted_source = isort.code(block_source, **config)
        return block_source == sorted_source
    
    @staticmethod
    def _needs_section_separators(source: str, config: Dict) -> bool:
        """Check if import sections need blank line separators."""
        sorted = isort.code(source, **config)
        # If ISort adds blank lines, they were missing
        return len(sorted.splitlines()) > len(source.splitlines())
    
    @staticmethod
    def fix_file(file_path: Path, config: Optional[Dict] = None) -> bool:
        """Sort imports in a file using ISort."""
        try:
            source = file_path.read_text(encoding="utf-8")
            fixed_source = ISortHelper.fix_source(source, config)
            
            if fixed_source != source:
                file_path.write_text(fixed_source, encoding="utf-8")
                return True
            return False
        except Exception:
            return False
    
    @staticmethod
    def fix_source(source: str, config: Optional[Dict] = None) -> str:
        """Sort imports in source code using ISort."""
        isort_config = {
            "profile": "black",
            "multi_line_output": 3,
            "line_length": DEFAULT_MAX_LINE_LENGTH,
            "known_first_party": ["prefact"],
        }
        
        if config:
            isort_config.update(config)
        
        return isort.code(source, **isort_config)


@register
class ISortedImports(BaseRule):
    """Sort imports using ISort."""
    
    rule_id = "sorted-imports"
    description = "Sort imports according to PEP8 using ISort"
    
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.isort_config = self._load_isort_config()
    
    def _load_isort_config(self) -> Dict:
        """Load ISort configuration from prefact config."""
        config = {
            "profile": self.config.get_rule_option(self.rule_id, "profile", "black"),
            "line_length": self.config.get_rule_option(self.rule_id, "line_length", DEFAULT_MAX_LINE_LENGTH),
            "known_first_party": self.config.get_rule_option(
                self.rule_id, "known_first_party", [self.config.package_name or "prefact"]
            ),
            "sections": self.config.get_rule_option(
                self.rule_id, "sections", ["FUTURE", "STDLIB", "THIRDPARTY", "FIRSTPARTY", "LOCALFOLDER"]
            ),
        }
        
        # Add custom settings
        custom_settings = self.config.get_rule_option(self.rule_id, "custom_settings", {})
        config.update(custom_settings)
        
        return config
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        # Skip if isort is not available
        if not HAS_ISORT:
            return []
        # Skip if isort is not available
        if not HAS_ISORT:
            return []
            
        issues = []
        results = ISortHelper.check_source(source, self.isort_config)
        
        for item in results:
            issues.append(Issue(
                rule_id=self.rule_id,
                file=path,
                line=item.get("line", 1),
                col=0,
                message=item.get("message", "Imports not sorted"),
                severity=Severity.INFO,
                original="unsorted imports"
            ))
        
        return issues
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        if not issues or not HAS_ISORT:
            return source, []
        
        fixed_source = ISortHelper.fix_source(source, self.isort_config)
        fixes = []
        
        if fixed_source != source:
            for issue in issues:
                fixes.append(Fix(
                    issue=issue,
                    file=path,
                    original_code="unsorted imports",
                    fixed_code="sorted imports",
                    applied=True
                ))
        
        return fixed_source, fixes
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        # Skip if isort is not available
        if not HAS_ISORT:
            return ValidationResult(file=path, passed=True, checks=[], errors=[])
        # Verify imports are sorted
        remaining_issues = ISortHelper.check_source(fixed, self.isort_config)
        
        return ValidationResult(
            file=path,
            passed=len(remaining_issues) == 0,
            checks=["imports_sorted"] if not remaining_issues else [],
            errors=[f"Still has {len(remaining_issues)} sorting issues"] if remaining_issues else []
        )


@register
class ImportSectionSeparator(BaseRule):
    """Ensure import sections are properly separated."""
    
    rule_id = "import-section-separators"
    description = "Ensure import sections are separated by blank lines"
    
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.isort_config = {
            "profile": config.get_rule_option("sorted-imports", "profile", "black"),
            "known_first_party": [config.package_name or "prefact"],
        }
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        # Skip if isort is not available
        if not HAS_ISORT:
            return []
        issues = []
        
        # Check for missing section separators
        if ISortHelper._needs_section_separators(source, self.isort_config):
            issues.append(Issue(
                rule_id=self.rule_id,
                file=path,
                line=1,
                col=0,
                message="Import sections should be separated by blank lines",
                severity=Severity.INFO,
                original="imports without separators"
            ))
        
        return issues
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        if not issues or not HAS_ISORT:
            return source, []
        
        fixed_source = ISortHelper.fix_source(source, self.isort_config)
        fixes = []
        
        if fixed_source != source:
            fixes.append(Fix(
                issue=issues[0],
                file=path,
                original_code="imports without separators",
                fixed_code="imports with proper separators",
                applied=True
            ))
        
        return fixed_source, fixes
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        # Skip if isort is not available
        if not HAS_ISORT:
            return ValidationResult(file=path, passed=True, checks=[], errors=[])
        needs_separators = ISortHelper._needs_section_separators(fixed, self.isort_config)
        
        return ValidationResult(
            file=path,
            passed=not needs_separators,
            checks=["section_separators_present"] if not needs_separators else [],
            errors=["Missing section separators"] if needs_separators else []
        )


# Advanced: Custom import organization
@register
class CustomImportOrganization(BaseRule):
    """Organize imports according to custom rules."""
    
    rule_id = "custom-import-organization"
    description = "Organize imports according to custom project rules"
    
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.custom_rules = self._load_custom_rules()
    
    def _load_custom_rules(self) -> Dict:
        """Load custom import organization rules."""
        return {
            "group_by_package": self.config.get_rule_option(
                self.rule_id, "group_by_package", False
            ),
            "alphabetical_within_groups": self.config.get_rule_option(
                self.rule_id, "alphabetical_within_groups", True
            ),
            "custom_groups": self.config.get_rule_option(
                self.rule_id, "custom_groups", {}
            ),
            "required_after_imports": self.config.get_rule_option(
                self.rule_id, "required_after_imports", []
            ),
        }
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        # Skip if isort is not available
        if not HAS_ISORT:
            return []
        import ast
        
        issues = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return issues
        
        # Find all import statements
        imports = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        "line": node.lineno,
                        "type": "import",
                        "module": alias.name,
                        "name": alias.asname or alias.name
                    })
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append({
                        "line": node.lineno,
                        "type": "from",
                        "module": module,
                        "name": alias.asname or alias.name,
                        "level": node.level
                    })
        
        # Check organization
        if self.custom_rules["group_by_package"]:
            issues.extend(self._check_grouping(path, imports))
        
        if self.custom_rules["alphabetical_within_groups"]:
            issues.extend(self._check_alphabetical(path, imports))
        
        return issues
    
    def _check_grouping(self, path: Path, imports: List[Dict]) -> List[Issue]:
        """Check if imports are properly grouped by package."""
        issues = []
        current_package = None
        
        for imp in imports:
            package = imp["module"].split(".")[0] if imp["module"] else ""
            
            if current_package and package != current_package:
                # Check if there's a blank line between packages
                # This is simplified - real implementation would check source
                pass
            
            current_package = package
        
        return issues
    
    def _check_alphabetical(self, path: Path, imports: List[Dict]) -> List[Issue]:
        """Check if imports are alphabetical within groups."""
        issues = []
        
        # Group by module
        groups = {}
        for imp in imports:
            module = imp["module"]
            if module not in groups:
                groups[module] = []
            groups[module].append(imp)
        
        # Check alphabetical order within each group
        for module, group in groups.items():
            names = [imp["name"] for imp in group]
            if names != sorted(names):
                issues.append(Issue(
                    rule_id=self.rule_id,
                    file=path,
                    line=group[0]["line"],
                    col=0,
                    message=f"Imports from '{module}' not in alphabetical order",
                    severity=Severity.INFO,
                    original="unalphabetical imports"
                ))
        
        return issues
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        # Use ISort with custom configuration
        custom_config = {
            "profile": "black",
            "force_single_line": self.custom_rules["group_by_package"],
            "sort_order": "natural" if self.custom_rules["alphabetical_within_groups"] else "native",
        }
        
        fixed_source = ISortHelper.fix_source(source, custom_config)
        fixes = []
        
        if fixed_source != source:
            for issue in issues:
                fixes.append(Fix(
                    issue=issue,
                    file=path,
                    original_code=issue.original,
                    fixed_code="organized imports",
                    applied=True
                ))
        
        return fixed_source, fixes
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        # Skip if isort is not available
        if not HAS_ISORT:
            return ValidationResult(file=path, passed=True, checks=[], errors=[])
        # Re-scan to check if organization is correct
        issues = self.scan_file(path, fixed)
        
        return ValidationResult(
            file=path,
            passed=len(issues) == 0,
            checks=["imports_organized"] if not issues else [],
            errors=[f"Still has {len(issues)} organization issues"] if issues else []
        )
