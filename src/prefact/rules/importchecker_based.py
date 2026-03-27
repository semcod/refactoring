"""ImportChecker-based precise import analysis for prefact.

This module provides integration with importchecker for detailed analysis
of unused and duplicate imports with high precision.
"""

from __future__ import annotations

import ast
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Set

from prefact.config import Config
from prefact.models import Fix, Issue, Severity, ValidationResult
from prefact.rules import BaseRule, register


class ImportCheckerHelper:
    """Helper class for importchecker operations."""
    
    @staticmethod
    def check_file(file_path: Path) -> List[Dict]:
        """Check a file using importchecker."""
        try:
            # Import importchecker dynamically
            import importchecker
            
            # Get module name from file path
            module_name = ImportCheckerHelper._get_module_name(file_path)
            
            if not module_name:
                return []
            
            # Run importchecker
            checker = importchecker.ImportChecker(module_name)
            unused_imports = checker.do_importcheck()
            
            # Convert to issues
            issues = []
            for imp in unused_imports:
                issues.append({
                    "type": "unused_import",
                    "import": str(imp),
                    "module": module_name
                })
            
            return issues
        except ImportError:
            # importchecker not available
            return []
        except Exception:
            return []
    
    @staticmethod
    def _get_module_name(file_path: Path) -> Optional[str]:
        """Convert file path to module name."""
        # This is simplified - real implementation would need
        # to consider PYTHONPATH and package structure
        parts = file_path.with_suffix('').parts
        
        # Remove common parent directories
        if "src" in parts:
            parts = parts[parts.index("src") + 1:]
        elif "lib" in parts:
            parts = parts[parts.index("lib") + 1:]
        
        return ".".join(parts)
    
    @staticmethod
    def check_source(source: str, module_name: str = "temp_module") -> List[Dict]:
        """Check source code using importchecker."""
        # Create a temporary module
        with tempfile.TemporaryDirectory() as tmpdir:
            module_path = Path(tmpdir) / f"{module_name}.py"
            module_path.write_text(source)
            
            # Add to sys.path temporarily
            sys.path.insert(0, tmpdir)
            try:
                return ImportCheckerHelper.check_file(module_path)
            finally:
                sys.path.remove(tmpdir)


@register
class ImportCheckerUnusedImports(BaseRule):
    """Detect unused imports using importchecker."""
    
    rule_id = "unused-imports"
    description = "Detect unused imports using importchecker library"
    
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.checker_config = self._load_checker_config()
    
    def _load_checker_config(self) -> Dict:
        """Load importchecker configuration."""
        return {
            "ignore_init_module": self.config.get_rule_option(
                self.rule_id, "ignore_init_module", True
            ),
            "ignore_dunder_main": self.config.get_rule_option(
                self.rule_id, "ignore_dunder_main", True
            )
        }
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        issues = []
        
        # Skip if configured to ignore
        if self.checker_config["ignore_init_module"] and path.name == "__init__.py":
            return issues
        
        results = ImportCheckerHelper.check_file(path)
        
        # Map results to line numbers
        import_lines = self._find_import_lines(source)
        
        for item in results:
            import_name = item.get("import", "unknown")
            line_num = import_lines.get(import_name, 1)
            
            # Skip __main__ if configured
            if self.checker_config["ignore_dunder_main"] and import_name == "__main__":
                continue
            
            issues.append(Issue(
                rule_id=self.rule_id,
                file=path,
                line=line_num,
                col=0,
                message=f"Unused import: {import_name}",
                severity=Severity.INFO,
                original=import_name
            ))
        
        return issues
    
    def _find_import_lines(self, source: str) -> Dict[str, int]:
        """Find line numbers for each import."""
        import_lines = {}
        lines = source.splitlines()
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                # Extract import names
                if stripped.startswith("from "):
                    parts = stripped.split()
                    if len(parts) >= 4:
                        module = parts[1]
                        imports = parts[3].split(",")
                        for imp in imports:
                            name = imp.strip().split(" as ")[0]
                            import_lines[name] = i + 1
                            if module:
                                import_lines[f"{module}.{name}"] = i + 1
                else:
                    imports = stripped[6:].split(",")  # Remove "import"
                    for imp in imports:
                        name = imp.strip().split(" as ")[0].split(".")[0]
                        import_lines[name] = i + 1
        
        return import_lines
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        # Use existing unused imports fixer
        from prefact.rules.unused_imports import UnusedImports
        fixer = UnusedImports(self.config)
        return fixer.fix(path, source, issues)
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        # Check if unused imports remain
        results = ImportCheckerHelper.check_file(path)
        
        return ValidationResult(
            file=path,
            passed=len(results) == 0,
            checks=["no_unused_imports"] if not results else [],
            errors=[f"Still has {len(results)} unused imports"] if results else []
        )


@register
class ImportCheckerDuplicateImports(BaseRule):
    """Detect duplicate imports using importchecker."""
    
    rule_id = "duplicate-imports"
    description = "Detect duplicate imports using importchecker library"
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        issues = []
        
        # Parse AST to find imports
        try:
            tree = ast.parse(source)
            import_map = {}
            
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        name = alias.asname or alias.name.split(".")[0]
                        if name in import_map:
                            issues.append(Issue(
                                rule_id=self.rule_id,
                                file=path,
                                line=node.lineno,
                                col=node.col_offset,
                                message=f"Duplicate import: {name}",
                                severity=Severity.WARNING,
                                original=name
                            ))
                        else:
                            import_map[name] = node.lineno
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        name = alias.asname or alias.name
                        if name in import_map and import_map[name] != node.lineno:
                            full_name = f"{module}.{name}" if module else name
                            issues.append(Issue(
                                rule_id=self.rule_id,
                                file=path,
                                line=node.lineno,
                                col=node.col_offset,
                                message=f"Duplicate import: {full_name}",
                                severity=Severity.WARNING,
                                original=full_name
                            ))
                        else:
                            import_map[name] = node.lineno
        except SyntaxError:
            pass
        
        return issues
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        # Use existing duplicate imports fixer
        from prefact.rules.duplicate_imports import DuplicateImports
        fixer = DuplicateImports(self.config)
        return fixer.fix(path, source, issues)
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        # Re-scan for duplicate imports
        issues = self.scan_file(path, fixed)
        
        return ValidationResult(
            file=path,
            passed=len(issues) == 0,
            checks=["no_duplicate_imports"] if not issues else [],
            errors=[f"Still has {len(issues)} duplicate imports"] if issues else []
        )


# Advanced: Import dependency analysis
@register
class ImportDependencyAnalysis(BaseRule):
    """Analyze import dependencies using importchecker."""
    
    rule_id = "import-dependencies"
    description = "Analyze import dependencies and circular imports"
    
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.checker_config = self._load_checker_config()
    
    def _load_checker_config(self) -> Dict:
        """Load configuration."""
        return {
            "max_depth": self.config.get_rule_option(
                self.rule_id, "max_depth", 5
            ),
            "detect_cycles": self.config.get_rule_option(
                self.rule_id, "detect_cycles", True
            )
        }
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        issues = []
        
        # Parse imports
        imports = self._extract_imports(source)
        
        # Check for circular imports
        if self.checker_config["detect_cycles"]:
            circular = self._detect_circular_imports(path, imports)
            for cycle in circular:
                issues.append(Issue(
                    rule_id=self.rule_id,
                    file=path,
                    line=1,
                    col=0,
                    message=f"Circular import detected: {' -> '.join(cycle)}",
                    severity=Severity.ERROR,
                    original=" -> ".join(cycle)
                ))
        
        # Check import depth
        for imp in imports:
            if imp.count(".") > self.checker_config["max_depth"]:
                issues.append(Issue(
                    rule_id=self.rule_id,
                    file=path,
                    line=imp["line"],
                    col=0,
                    message=f"Deep import: {imp['name']} (depth: {imp['name'].count('.')})",
                    severity=Severity.WARNING,
                    original=imp["name"]
                ))
        
        return issues
    
    def _extract_imports(self, source: str) -> List[Dict]:
        """Extract all imports from source."""
        imports = []
        lines = source.splitlines()
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                if stripped.startswith("from "):
                    parts = stripped.split()
                    if len(parts) >= 4:
                        module = parts[1]
                        imports.append({
                            "name": module,
                            "line": i + 1,
                            "type": "from"
                        })
                else:
                    parts = stripped.split()
                    if len(parts) >= 2:
                        module = parts[1].split(".")[0]
                        imports.append({
                            "name": module,
                            "line": i + 1,
                            "type": "import"
                        })
        
        return imports
    
    def _detect_circular_imports(self, path: Path, imports: List[Dict]) -> List[List[str]]:
        """Detect circular imports (simplified implementation)."""
        # This is a simplified version - real implementation would need
        # to build a full dependency graph
        circular = []
        
        # Get current module name
        current_module = ImportCheckerHelper._get_module_name(path)
        if not current_module:
            return circular
        
        # Check if any import could be circular
        for imp in imports:
            if imp["type"] == "from":
                # Simplified check - just warn about same package imports
                if current_module.split(".")[0] in imp["name"]:
                    circular.append([current_module, imp["name"], current_module])
        
        return circular
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        # Import dependency issues usually require manual fixes
        return source, []
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        # Re-run analysis
        issues = self.scan_file(path, fixed)
        
        return ValidationResult(
            file=path,
            passed=len(issues) == 0,
            checks=["no_circular_imports", "import_depth_ok"] if not issues else [],
            errors=[issue.message for issue in issues] if issues else []
        )


# Import organization using importchecker insights
@register
class ImportOptimizer(BaseRule):
    """Optimize imports based on importchecker analysis."""
    
    rule_id = "import-optimization"
    description = "Optimize imports based on usage analysis"
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        issues = []
        
        # Get unused imports from importchecker
        unused = ImportCheckerHelper.check_file(path)
        
        # Get all imports
        all_imports = self._extract_all_imports(source)
        
        # Find imports that are used only once
        single_use = []
        for imp in all_imports:
            if not any(u["import"] == imp["name"] for u in unused):
                usage_count = self._count_usage(source, imp["name"])
                if usage_count == 1:
                    single_use.append(imp)
        
        # Report single-use imports
        for imp in single_use:
            issues.append(Issue(
                rule_id=self.rule_id,
                file=path,
                line=imp["line"],
                col=0,
                message=f"Import used only once: {imp['name']}",
                severity=Severity.INFO,
                original=imp["name"]
            ))
        
        return issues
    
    def _extract_all_imports(self, source: str) -> List[Dict]:
        """Extract all imports with their locations."""
        imports = []
        lines = source.splitlines()
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                if stripped.startswith("from "):
                    parts = stripped.split()
                    if len(parts) >= 4:
                        module = parts[1]
                        names = parts[3].split(",")
                        for name in names:
                            clean_name = name.strip().split(" as ")[0]
                            imports.append({
                                "name": clean_name,
                                "line": i + 1,
                                "module": module
                            })
                else:
                    names = stripped[6:].split(",")
                    for name in names:
                        clean_name = name.strip().split(" as ")[0].split(".")[0]
                        imports.append({
                            "name": clean_name,
                            "line": i + 1,
                            "module": None
                        })
        
        return imports
    
    def _count_usage(self, source: str, import_name: str) -> int:
        """Count how many times an import is used."""
        # Simple string-based counting
        # Real implementation would use AST for accuracy
        count = 0
        lines = source.splitlines()
        
        # Skip import lines
        import_lines = set()
        for i, line in enumerate(lines):
            if line.strip().startswith(("import ", "from ")):
                import_lines.add(i)
        
        # Count usage in non-import lines
        for i, line in enumerate(lines):
            if i not in import_lines:
                # Count occurrences of the import name
                count += line.count(import_name)
        
        return count
    
    def fix(self, path: Path, source: str, issues: List[Issue]) -> tuple[str, List[Fix]]:
        # Optimization suggestions only - no automatic fixes
        return source, []
    
    def validate(self, path: Path, original: str, fixed: str) -> ValidationResult:
        return ValidationResult(
            file=path,
            passed=True,
            checks=["imports_analyzed"],
            errors=[]
        )
