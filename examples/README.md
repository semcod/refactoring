# prefact Examples

> 📚 **Main Documentation**: See the [main README.md](../README.md) for installation and usage instructions.

This directory contains comprehensive examples demonstrating all features of the prefact library, including new enterprise capabilities.

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
├── 06-api-usage/           # Python API examples
├── 07-enterprise/          # 🆕 Complete enterprise configuration
├── 08-llm-focused/         # 🆕 LLM-specific optimizations
├── 09-high-performance/    # 🆕 Performance-optimized settings
├── 10-plugin-development/  # 🆕 Plugin development setup
├── 11-ci-cd/               # 🆕 Updated CI/CD examples
└── 12-complete-example/    # 🆕 Comprehensive reference
```

## 🆕 Enterprise Features

The new examples showcase prefact's enterprise capabilities:

### 1. [Enterprise Configuration](./07-enterprise/prefact.yaml)
Complete enterprise setup with:
- All tool integrations (Ruff, MyPy, ISort, Pylint, etc.)
- LLM-specific rules for AI-generated code
- Plugin system with marketplace support
- Performance optimization with parallel processing
- Environment-specific configurations
- Telemetry and monitoring

### 2. [LLM-Focused Configuration](./08-llm-focused/prefact.yaml)
Optimized for projects with AI-generated code:
- Comprehensive hallucination detection
- Custom patterns for specific LLMs
- Template/placeholder code detection
- Incomplete implementation warnings

### 3. [High-Performance Configuration](./09-high-performance/prefact.yaml)
For large codebases:
- Maximum parallelization (16 workers)
- Aggressive caching (2GB)
- Tool-specific optimizations
- CI/CD performance profiles

### 4. [Plugin Development](./10-plugin-development/prefact.yaml)
For custom plugin development:
- Multiple plugin directories
- Auto-reload in development
- Plugin validation
- Custom registry support

### 5. [Updated CI/CD](./11-ci-cd/prefact.yaml)
Modern CI/CD integration:
- GitHub Actions, GitLab CI, Jenkins support
- Fast feedback rules
- Environment-specific optimizations
- JSON output for parsing

### 6. [Complete Reference](./12-complete-example/prefact.yaml)
Comprehensive example with all features:
- Every rule and tool configured
- All environment variables
- Full plugin setup
- Complete telemetry configuration

## Key Enterprise Features

### Tool Integrations
```yaml
tools:
  ruff:
    enabled: true
    max_line_length: 88
  mypy:
    enabled: true
    strict: true
  pylint:
    enabled: true
    disable_codes: "R0903"
```

### LLM-Specific Rules
```yaml
rules:
  llm-hallucinations:
    enabled: true
    patterns:
      - pattern: "TODO: implement"
        severity: "error"
  magic-numbers:
    enabled: true
    threshold: 10
```

### Performance Optimization
```yaml
performance:
  max_workers: 16
  cache: true
  cache_size: 2147483648  # 2GB
  parallel: true
```

### Plugin System
```yaml
plugins:
  enabled: true
  directories:
    - "~/.prefact/plugins"
    - "./.prefact/plugins"
```

### Environment Configurations
```yaml
environments:
  production:
    rules:
      print-statements:
        enabled: false
  development:
    _logging:
      level: "DEBUG"
```

### Composite Rules
```yaml
rules:
  composite-imports:
    enabled: true
    strategy: "parallel"
    tools: ["unused-imports", "duplicate-imports"]
```

## 🚀 Getting Started

1. **Install prefact with enterprise features**:
   ```bash
   pip install prefact[all]
   # or specific tools
   pip install prefact[ruff,mypy,isort,performance]
   ```

2. **Try the enterprise sample**:
   ```bash
   cd examples/07-enterprise
   prefact scan --path . --config prefact.yaml
   prefact fix --path . --config prefact.yaml
   ```

3. **Copy an example for your project**:
   ```bash
   cp examples/07-enterprise/prefact.yaml ./prefact.yaml
   # Edit to match your project
   ```

## Environment Variables

Enterprise configurations support environment variables:
- `PREFACT_CACHE_DIR` - Cache directory location
- `PREFACT_LOG_LEVEL` - Logging level
- `PREFACT_TELEMETRY_KEY` - Telemetry API key
- `ENTERPRISE_API_KEY` - Enterprise features key
- `PREFACT_PLUGIN_DIR` - Plugin directory

## Migration Guide

Upgrading from basic to enterprise configuration:

1. Backup current `prefact.yaml`
2. Copy enterprise example:
   ```bash
   cp examples/07-enterprise/prefact.yaml ./prefact.yaml.new
   ```
3. Merge your custom settings
4. Test with `--dry-run`
5. Gradually enable new features
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
