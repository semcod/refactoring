# Migration Guide: AST Rules to Ruff-based Implementation

This guide helps you migrate from AST-based rules to faster Ruff-based implementations in prefact.

## Why Migrate to Ruff?

### Performance Benefits
- **10-100x faster** than AST-based implementations
- Single pass can detect multiple rule violations
- Written in Rust for optimal performance

### Maintenance Benefits
- Battle-tested implementation
- Covers edge cases you might not have considered
- Regular updates with new rule implementations

## Migration Overview

### Rules That Can Be Migrated

| Rule | AST Implementation | Ruff Equivalent | Migration Complexity |
|------|-------------------|-----------------|---------------------|
| unused-imports | Custom AST walker | F401 | Low |
| wildcard-imports | AST pattern matching | F403 | Low |
| print-statements | AST visitor | T201 | Low |
| sorted-imports | Custom sorting logic | I001, I002 | Medium |
| duplicate-imports | AST tracking | F811 (partial) | High |

### Rules to Keep as AST-based

| Rule | Reason to Keep AST |
|------|-------------------|
| relative-imports | Requires package context and complex path resolution |
| string-concat | Requires transformation to f-strings |
| missing-return-type | Requires type checking (mypy integration) |

## Step-by-Step Migration

### Step 1: Install Ruff

```bash
pip install ruff
```

### Step 2: Update Dependencies

Add to `pyproject.toml`:

```toml
[project.optional-dependencies]
ruff = [
    "ruff>=0.1.0",
]
```

### Step 3: Enable Ruff Rules in Configuration

Update your `prefact.yaml`:

```yaml
package_name: planfile

# Existing configuration...
rules:
  unused-imports:
    enabled: true
    use_ruff: true  # Use Ruff implementation
  wildcard-imports:
    enabled: true
    use_ruff: true
  print-statements:
    enabled: true
    use_ruff: true
  sorted-imports:
    enabled: true
    use_ruff: true

# New Ruff-specific section
ruff:
  enabled: true
  ignore_patterns: 
    - "cli.py"
    - "scripts/"
```

### Step 4: Update Rule Registration

Modify `src/prefact/rules/__init__.py`:

```python
# Add Ruff-based imports
from prefact.rules.ruff_based import (
    RuffUnusedImports as _ruff_unused,
    RuffWildcardImports as _ruff_wildcard,
    RuffPrintStatements as _ruff_print,
    RuffSortedImports as _ruff_sorted,
)

# Update registration logic
def get_rule(rule_id: str, config: Config) -> BaseRule:
    """Get rule instance, preferring Ruff if enabled."""
    ruff_rules = {
        "unused-imports": _ruff_unused,
        "wildcard-imports": _ruff_wildcard,
        "print-statements": _ruff_print,
        "sorted-imports": _ruff_sorted,
    }
    
    if rule_id in ruff_rules and config.get_rule_option(rule_id, "use_ruff", False):
        return ruff_rules[rule_id](config)
    
    return _REGISTRY[rule_id](config)
```

### Step 5: Test Migration

Run the benchmark tool to compare performance:

```bash
python -m prefact.rules.benchmark --path ./your_project
```

Expected output:
```
PERFORMANCE BENCHMARK RESULTS
============================================================

Project: ./your_project
Files processed: 150

Total AST time: 1250.00 ms
Total Ruff time: 45.00 ms
Overall speedup: 27.78x
```

### Step 6: Gradual Rollout

Start with a subset of rules:

```python
# In your config
MIGRATION_PHASES = {
    1: ["unused-imports", "wildcard-imports"],
    2: ["print-statements"],
    3: ["sorted-imports"],
}
```

## Custom Ruff Rules

### Creating Custom Ruff-based Rules

```python
from prefact.rules.ruff_based import RuffHelper

@register
class CustomRuffRule(BaseRule):
    """Custom rule using Ruff's API."""
    
    rule_id = "custom-rule"
    description = "Custom rule implemented with Ruff"
    
    # Map to Ruff codes
    RUFF_CODES = ["E501", "W503"]  # line too long, line break before binary operator
    
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        results = RuffHelper.check_file(path, self.RUFF_CODES)
        return [Issue.from_ruff(item) for item in results]
```

### Ruff Configuration

Create `ruff.toml` in your project:

```toml
[tool.ruff]
target-version = "py311"
line-length = 88

[tool.ruff.lint]
select = ["F", "E", "W", "I", "T"]
ignore = ["E501"]  # Ignore line too long

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]  # Allow unused imports in __init__.py
"tests/*" = ["T201"]      # Allow print in tests
```

## Troubleshooting

### Issue: Ruff doesn't detect some cases

**Solution**: Create hybrid rules

```python
class HybridUnusedImports(BaseRule):
    def scan_file(self, path: Path, source: str) -> List[Issue]:
        # First try Ruff
        ruff_issues = self.ruff_rule.scan_file(path, source)
        
        # Fall back to AST for edge cases
        ast_issues = self.ast_rule.scan_file(path, source)
        
        # Merge results, avoiding duplicates
        return self.merge_issues(ruff_issues, ast_issues)
```

### Issue: Performance is worse than expected

**Checklist**:
1. Ensure Ruff is installed correctly
2. Verify you're not running Ruff for each file individually
3. Use batch processing for large projects

```python
# Bad: Running Ruff per file
for file in files:
    RuffHelper.check_file(file, codes)

# Good: Batch processing
def check_batch(files: List[Path], codes: List[str]) -> Dict[Path, List[Issue]]:
    result = subprocess.run([
        "ruff", "check", *[str(f) for f in files],
        "--select", ",".join(codes),
        "--format", "json"
    ], capture_output=True)
    return parse_ruff_output(result.stdout)
```

### Issue: Ruff fixes break formatting

**Solution**: Combine with formatters

```python
def fix_with_preserved_formatting(path: Path, issues: List[Issue]) -> str:
    # 1. Apply Ruff fixes
    RuffHelper.fix_file(path, ["F401"])
    
    # 2. Reformat with black
    subprocess.run(["black", str(path)])
    
    # 3. Reformat with isort
    subprocess.run(["isort", str(path)])
    
    return path.read_text()
```

## Best Practices

### 1. Configuration Management

```yaml
# prefact.yaml
rules:
  unused-imports:
    enabled: true
    implementation: "ruff"  # "ast" or "ruff"
    fallback_to_ast: true   # Use AST if Ruff fails
```

### 2. Error Handling

```python
def safe_ruff_scan(path: Path, codes: List[str]) -> List[Dict]:
    try:
        return RuffHelper.check_file(path, codes)
    except Exception as e:
        logger.warning(f"Ruff failed on {path}: {e}")
        return []
```

### 3. Testing Migration

```python
def test_rule_equivalence():
    """Ensure Ruff and AST implementations find same issues."""
    test_files = Path("test_cases").glob("*.py")
    
    for file_path in test_files:
        source = file_path.read_text()
        
        ast_issues = ast_rule.scan_file(file_path, source)
        ruff_issues = ruff_rule.scan_file(file_path, source)
        
        assert len(ast_issues) == len(ruff_issues), (
            f"Mismatch in {file_path}: "
            f"AST={len(ast_issues)}, Ruff={len(ruff_issues)}"
        )
```

## Performance Optimization Tips

### 1. Parallel Processing

```python
from concurrent.futures import ThreadPoolExecutor

def parallel_ruff_scan(files: List[Path]) -> Dict[Path, List[Issue]]:
    with ThreadPoolExecutor() as executor:
        results = executor.map(
            lambda f: (f, RuffHelper.check_file(f, ["F401"])),
            files
        )
    return dict(results)
```

### 2. Caching

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_ruff_check(file_hash: str, codes: tuple) -> List[Dict]:
    # Check file hash to detect changes
    return RuffHelper.check_file(file_path, list(codes))
```

### 3. Incremental Scanning

```python
def scan_incremental(changes: Dict[Path, str]) -> Dict[Path, List[Issue]]:
    """Only scan changed files."""
    results = {}
    for file_path, content_hash in changes.items():
        if is_file_changed(file_path, content_hash):
            results[file_path] = RuffHelper.check_file(file_path, ["F401"])
    return results
```

## Migration Checklist

- [ ] Install Ruff
- [ ] Update dependencies in pyproject.toml
- [ ] Add Ruff configuration
- [ ] Implement Ruff-based rules
- [ ] Update rule registration
- [ ] Run benchmarks
- [ ] Test on sample files
- [ ] Update documentation
- [ ] Gradual rollout to users
- [ ] Monitor performance in production

## Next Steps

After migrating basic rules to Ruff, consider:

1. **Advanced Ruff Features**: Explore custom rule plugins
2. **Type Checking Integration**: Add mypy for missing-return-type
3. **IDE Integration**: Create language server extensions
4. **CI/CD Optimization**: Optimize for CI pipelines

## Support

For issues during migration:
1. Check the benchmark tool output
2. Review Ruff documentation
3. Use hybrid rules for complex cases
4. Report issues to the prefact repository
