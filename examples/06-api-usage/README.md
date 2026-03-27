# Python API Usage Example

This example shows how to use prefact programmatically from Python code.

## Basic Usage

The `example.py` file demonstrates:
- Creating a Config object
- Initializing RefactoringEngine
- Running scans and fixes
- Processing results

## Use Cases

1. **IDE Integration**: Add prefact to your editor/IDE
2. **Pre-commit Hooks**: Run checks before commits
3. **Custom Scripts**: Build custom refactoring tools
4. **Batch Processing**: Process multiple projects
5. **Reporting**: Generate custom reports

## Running

```bash
# Run the example
python example.py

# Run with custom config
python example.py --config custom.yaml
```

## Key Classes

- `Config` - Configuration for prefact
- `RefactoringEngine` - Main engine for running rules
- `Issue` - Represents a detected issue
- `Fix` - Represents an applied fix
- `ValidationResult` - Result of validation after fixes

## Error Handling

The example shows proper error handling for:
- Invalid configuration
- Parse errors in source files
- Validation failures
