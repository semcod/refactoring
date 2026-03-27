# Sample Project for prefact

> 📚 **Back to Examples**: [See all examples](../README.md) | 📖 **Main Docs**: [prefact README.md](../../README.md)

This is a deliberately messy Python project that demonstrates all the issues that prefact can fix.

## Issues Present

- **Relative imports**: Using `from ..module import` instead of absolute imports
- **Unused imports**: Imports that are never referenced
- **Duplicate imports**: Same module imported multiple times
- **Wildcard imports**: Using `from module import *`
- **Unsorted imports**: Imports not in stdlib→3rd-party→local order
- **String concatenation**: Using `"Hello " + name` instead of f-strings
- **Print statements**: Debug print statements left in code
- **Missing return types**: Functions without return type annotations

## Files

- `core.py` - Main module with various issues
- `utils.py` - Utility functions with problems
- `models.py` - Data models with import issues
- `cli.py` - CLI module with print statements

Run prefact on this project to see it transform the code!
