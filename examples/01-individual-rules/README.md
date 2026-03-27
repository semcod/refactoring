# Individual Rule Examples

> 📚 **Back to Examples**: [See all examples](../README.md) | 📖 **Main Docs**: [prefact README.md](../../README.md)

This directory contains examples for each individual prefact rule.

## Structure

Each subdirectory demonstrates a specific rule:
- `relative-imports` - Converting relative imports to absolute
- `unused-imports` - Removing unused imports
- `duplicate-imports` - Removing duplicate imports
- `wildcard-imports` - Detecting wildcard imports
- `sorted-imports` - Detecting unsorted imports
- `string-concat` - Converting string concatenation to f-strings
- `print-statements` - Finding print statements
- `missing-return-type` - Adding return type annotations

## Running Examples

```bash
# Navigate to specific rule directory
cd examples/01-individual-rules/relative-imports

# Run prefact on the example
prefact scan --path . --config prefact.yaml

# Fix the issues
prefact fix --path . --config prefact.yaml
```
