# Multiple Rules Example

This example shows how to combine multiple prefact rules to clean up code comprehensively.

## Scenario

We have a Python module with multiple issues:
- Relative imports
- Unused imports
- String concatenation
- Print statements
- Missing return type annotations

## Running the Example

```bash
# Scan for all issues
prefact scan --path . --config prefact.yaml

# Fix all auto-fixable issues
prefact fix --path . --config prefact.yaml

# Check what was fixed
git diff
```

## Configuration

The `prefact.yaml` enables multiple rules at once, showing how to configure severity levels for each rule.
