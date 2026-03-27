"""
Core refactoring engine for code analysis and transformation.
"""

import ast
from typing import List, Dict, Any, Optional


class RefactoringEngine:
    """Main engine for performing code refactoring operations."""
    
    def __init__(self):
        self.transformations = []
    
    def analyze_code(self, code: str) -> Dict[str, Any]:
        """Analyze Python code and return structural information."""
        try:
            tree = ast.parse(code)
            return {
                "success": True,
                "tree": tree,
                "functions": self._extract_functions(tree),
                "classes": self._extract_classes(tree),
                "imports": self._extract_imports(tree)
            }
        except SyntaxError as e:
            return {
                "success": False,
                "error": str(e),
                "line": e.lineno
            }
    
    def _extract_functions(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract function definitions from AST."""
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append({
                    "name": node.name,
                    "line": node.lineno,
                    "args": [arg.arg for arg in node.args.args],
                    "docstring": ast.get_docstring(node)
                })
        return functions
    
    def _extract_classes(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract class definitions from AST."""
        classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append({
                    "name": node.name,
                    "line": node.lineno,
                    "bases": [base.id for base in node.bases if isinstance(base, ast.Name)],
                    "methods": [n.name for n in node.body if isinstance(n, ast.FunctionDef)],
                    "docstring": ast.get_docstring(node)
                })
        return classes
    
    def _extract_imports(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract import statements from AST."""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        "type": "import",
                        "module": alias.name,
                        "alias": alias.asname,
                        "line": node.lineno
                    })
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imports.append({
                        "type": "from_import",
                        "module": node.module,
                        "name": alias.name,
                        "alias": alias.asname,
                        "line": node.lineno
                    })
        return imports
