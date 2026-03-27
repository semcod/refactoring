# prefact Examples

This directory contains comprehensive examples demonstrating all features of the prefact library.

## 📁 Directory Structure

```
examples/
├── README.md                 # This file - detailed guide
├── run_all.sh               # Script to validate all examples
├── generate_examples.py     # Helper script for generating examples
├── sample-project/          # Realistic project with all issues
├── 01-individual-rules/     # Each rule demonstrated separately
│   ├── relative-imports/
│   ├── unused-imports/
│   ├── duplicate-imports/
│   ├── wildcard-imports/
│   ├── sorted-imports/
│   ├── string-concat/
│   ├── print-statements/
│   └── missing-return-type/
├── 02-multiple-rules/       # Combining multiple rules
├── 03-output-formats/       # Console vs JSON output
├── 04-custom-rules/         # Writing custom rules
├── 05-ci-cd/               # CI/CD integration examples
└── 06-api-usage/           # Python API examples
```

## 🚀 Getting Started

1. **Install prefact**:
   ```bash
   pip install prefact
   # or from source
   pip install -e /path/to/prefact
   ```

2. **Try the sample project**:
   ```bash
   cd examples/sample-project
   prefact scan --path . --config prefact.yaml
   prefact fix --path . --config prefact.yaml
   ```

3. **Explore individual examples**:
   ```bash
   cd examples/01-individual-rules/relative-imports
   prefact scan --path . --config prefact.yaml
   ```

## 📚 Example Details

### sample-project/
A complete but messy Python project demonstrating all 8 rules that prefact can fix. Perfect for understanding the full scope of prefact's capabilities.

**Files**: `core.py`, `utils.py`, `models.py`, `cli.py`
**Issues**: Relative imports, unused imports, duplicates, wildcards, unsorted imports, string concatenation, print statements, missing return types

### 01-individual-rules/
Each subdirectory focuses on a single rule with:
- `prefact.yaml` - Configuration for that rule only
- `before.py` - Code with the issue
- `after.py` - Code after prefact fixes it (when applicable)
- `README.md` - Rule-specific explanation

### 02-multiple-rules/
Shows how to combine multiple rules to clean up code comprehensively. Demonstrates priority handling and how different rules interact.

### 03-output-formats/
Demonstrates the different output formats:
- Console output (human-readable, colored)
- JSON output (machine-readable, for CI/CD)
- Saving reports to files

### 04-custom-rules/
Complete example of writing custom rules:
- `no_todo_rule.py` - Detects TODO comments
- `custom_rules/` - Directory for custom rule implementations
- Shows the `@register` decorator pattern
- Demonstrates rule validation

### 05-ci-cd/
Production-ready CI/CD configurations:
- **GitHub Actions** (`.github/workflows/prefact.yml`)
  - Runs on PRs and pushes
  - Comments on PRs with results
  - Uploads reports as artifacts
- **GitLab CI** (`.gitlab-ci.yml`)
- **Azure DevOps** (`azure-pipelines.yml`)
- **Jenkins** (`Jenkinsfile`)

### 06-api-usage/
Programmatic usage examples:
- `example.py` - Complete script showing API usage
- Custom configuration
- Batch processing multiple projects
- Error handling
- Custom rule integration

## 🔧 Running All Examples

Use the provided script to validate all examples:

```bash
cd examples
chmod +x run_all.sh
./run_all.sh
```

This will:
1. Run prefact on each example
2. Verify fixes work correctly
3. Check that examples are up-to-date
4. Report any failures

## 📝 Best Practices Demonstrated

1. **Configuration**: Each example shows optimal `prefact.yaml` settings
2. **Exclusions**: Proper exclusion of `__pycache__`, `venv`, etc.
3. **Severity Levels**: Appropriate severity for different rules
4. **CI Integration**: Failing builds on new issues
5. **Gradual Adoption**: Starting with scan-only rules
6. **Custom Rules**: Extending prefact for project-specific needs

## 🤝 Contributing Examples

To add a new example:

1. Create a new directory following the naming convention
2. Include a `README.md` explaining the use case
3. Provide `prefact.yaml` configuration
4. Add sample files with issues
5. Update this `README.md` and `run_all.sh`
6. Test with `./run_all.sh`

## 🔍 Common Patterns

### LLM-Generated Code Fixes
```yaml
rules:
  relative-imports:
    enabled: true
    severity: warning  # LLMs often break imports
  unused-imports:
    enabled: true
    severity: info
```

### Production Code Cleanup
```yaml
rules:
  print-statements:
    enabled: true
    severity: error    # No prints in production
  wildcard-imports:
    enabled: true
    severity: warning
```

### Code Quality Enforcement
```yaml
rules:
  missing-return-type:
    enabled: true
    severity: info
  sorted-imports:
    enabled: true
    severity: info
```

## 📊 Performance Tips

1. **Large Projects**: Use `--package` to limit scope
2. **CI/CD**: Cache dependencies between runs
3. **Incremental**: Check only changed files in PRs
4. **Parallel**: Run multiple rules simultaneously
5. **Exclude**: Exclude generated code and third-party

## 🐛 Troubleshooting

- **"No issues found"**: Check your `include/exclude` patterns
- **"Import errors"**: Ensure the package name is correct
- **"Validation failed"**: Check for syntax errors in source files
- **Performance**: Use excludes for large directories

For more help, see the main [README.md](../README.md) or open an issue.
