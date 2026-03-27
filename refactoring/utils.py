"""
Utility functions for code parsing and analysis.
"""

import ast
from typing import Dict, List, Any, Optional
from pathlib import Path


def parse_code(file_path: str) -> Dict[str, Any]:
    """Parse a Python file and return its AST and metadata."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        tree = ast.parse(code)
        return {
            "success": True,
            "file_path": file_path,
            "code": code,
            "tree": tree,
            "lines": code.splitlines()
        }
    except (SyntaxError, FileNotFoundError, UnicodeDecodeError) as e:
        return {
            "success": False,
            "error": str(e),
            "file_path": file_path
        }


def analyze_structure(tree: ast.AST) -> Dict[str, Any]:
    """Analyze the structure of an AST and return detailed information."""
    structure = {
        "functions": [],
        "classes": [],
        "variables": [],
        "imports": [],
        "complexity": 0
    }
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            structure["functions"].append({
                "name": node.name,
                "line": node.lineno,
                "args": [arg.arg for arg in node.args.args],
                "decorators": [d.id if isinstance(d, ast.Name) else str(d) for d in node.decorator_list],
                "returns": ast.unparse(node.returns) if node.returns else None,
                "docstring": ast.get_docstring(node)
            })
            structure["complexity"] += _calculate_complexity(node)
        
        elif isinstance(node, ast.ClassDef):
            structure["classes"].append({
                "name": node.name,
                "line": node.lineno,
                "bases": [base.id for base in node.bases if isinstance(base, ast.Name)],
                "methods": [n.name for n in node.body if isinstance(n, ast.FunctionDef)],
                "docstring": ast.get_docstring(node)
            })
        
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    structure["variables"].append({
                        "name": target.id,
                        "line": node.lineno,
                        "type": "variable"
                    })
        
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    structure["imports"].append({
                        "type": "import",
                        "module": alias.name,
                        "alias": alias.asname,
                        "line": node.lineno
                    })
            else:
                for alias in node.names:
                    structure["imports"].append({
                        "type": "from_import",
                        "module": node.module,
                        "name": alias.name,
                        "alias": alias.asname,
                        "line": node.lineno
                    })
    
    return structure


def _calculate_complexity(node: ast.AST) -> int:
    """Calculate cyclomatic complexity of a function."""
    complexity = 1  # Base complexity
    
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.While, ast.For, ast.With)):
            complexity += 1
        elif isinstance(child, ast.ExceptHandler):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            complexity += len(child.values) - 1
    
    return complexity


def get_file_stats(file_path: str) -> Dict[str, Any]:
    """Get basic statistics about a Python file."""
    path = Path(file_path)
    
    if not path.exists():
        return {"success": False, "error": "File not found"}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        code = ''.join(lines)
        tree = ast.parse(code)
        structure = analyze_structure(tree)
        
        return {
            "success": True,
            "file_path": file_path,
            "total_lines": len(lines),
            "code_lines": len([line for line in lines if line.strip() and not line.strip().startswith('#')]),
            "comment_lines": len([line for line in lines if line.strip().startswith('#')]),
            "blank_lines": len([line for line in lines if not line.strip()]),
            "functions": len(structure["functions"]),
            "classes": len(structure["classes"]),
            "complexity": structure["complexity"]
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}
