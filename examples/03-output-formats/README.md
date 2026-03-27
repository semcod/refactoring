# Output Formats Example

This example demonstrates the different output formats supported by prefact.

## Available Formats

1. **Console** - Human-readable colored output (default)
2. **JSON** - Machine-readable output for CI/CD integration

## Console Output

```bash
# Default console output
prefact scan --path . --config prefact.yaml

# Explicit console output
prefact scan --path . --config prefact.yaml --format console
```

The console output shows:
- A table with issue details
- Color-coded severity levels
- Summary statistics

## JSON Output

```bash
# Generate JSON report
prefact scan --path . --config prefact.yaml --format json

# Save JSON to file
prefact scan --path . --config prefact.yaml --format json -o report.json

# JSON with fix operation
prefact fix --path . --config prefact.yaml --format json -o fix-report.json
```

The JSON output includes:
- Complete issue details with line numbers
- Fix information when using `fix` command
- Validation results
- Metadata about the scan

## Example JSON Structure

See `sample-report.json` for a complete example of the JSON output format.
