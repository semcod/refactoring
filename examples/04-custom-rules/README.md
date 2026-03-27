# Custom Rules Example

This example shows how to write custom refactoring rules for prefact.

## Creating a Custom Rule

Custom rules extend the `BaseRule` class and use the `@register` decorator:

1. Implement `scan_file()` - detect issues
2. Implement `fix()` - apply fixes (optional)
3. Implement `validate()` - validate fixes

## Example: No-TODO Rule

This custom rule detects TODO comments in code and optionally converts them to proper task tracking.

## Structure

- `custom_rules/` - Directory containing custom rule implementations
- `example_code.py` - Sample code to test the rule
- `prefact.yaml` - Configuration including the custom rule

## Running

```bash
# Scan with custom rule
prefact scan --path . --config prefact.yaml

# Fix with custom rule (if fix is implemented)
prefact fix --path . --config prefact.yaml
```

## Loading Custom Rules

Custom rules are automatically discovered if:
1. They're in a file imported by your project
2. They use the `@register` decorator
3. The rule ID is unique

You can also load rules from a separate package by importing them in your project's `__init__.py`.
