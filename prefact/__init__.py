"""
Prefact package for code analysis and transformation tools.
"""

__version__ = "0.0.6"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .core import RefactoringEngine
from .utils import parse_code, analyze_structure

__all__ = [
    "RefactoringEngine",
    "parse_code", 
    "analyze_structure"
]
