<!-- code2docs:start --># prefact

![version](https://img.shields.io/badge/version-0.1.0-blue) ![python](https://img.shields.io/badge/python-%3E%3D3.8-blue) ![coverage](https://img.shields.io/badge/coverage-unknown-lightgrey) ![functions](https://img.shields.io/badge/functions-655-green)
> **655** functions | **132** classes | **78** files | CC̄ = 3.0

> Auto-generated project documentation from source code analysis.

**Author:** Tom Sapletta  
**License:** Apache-2.0[(LICENSE)](./LICENSE)  
**Repository:** [https://github.com/semcod/refactoring](https://github.com/semcod/refactoring)

## Installation

### From PyPI

```bash
pip install prefact
```

### From Source

```bash
git clone https://github.com/semcod/refactoring
cd prefact
pip install -e .
```

### Optional Extras

```bash
pip install prefact[ruff]    # ruff features
pip install prefact[mypy]    # mypy features
pip install prefact[isort]    # isort features
pip install prefact[autoflake]    # autoflake features
pip install prefact[pylint]    # pylint features
pip install prefact[unimport]    # unimport features
pip install prefact[importchecker]    # importchecker features
pip install prefact[import-linter]    # import-linter features
pip install prefact[performance]    # performance features
pip install prefact[monitoring]    # monitoring features
pip install prefact[dev]    # development tools
pip install prefact[docs]    # documentation tools
pip install prefact[all]    # all optional features
```

## Quick Start

### CLI Usage

```bash
# Generate full documentation for your project
prefact ./my-project

# Only regenerate README
prefact ./my-project --readme-only

# Preview what would be generated (no file writes)
prefact ./my-project --dry-run

# Check documentation health
prefact check ./my-project

# Sync — regenerate only changed modules
prefact sync ./my-project
```

### Python API

```python
from prefact import generate_readme, generate_docs, Code2DocsConfig

# Quick: generate README
generate_readme("./my-project")

# Full: generate all documentation
config = Code2DocsConfig(project_name="mylib", verbose=True)
docs = generate_docs("./my-project", config=config)
```

## Generated Output

When you run `prefact`, the following files are produced:

```
<project>/
├── README.md                 # Main project README (auto-generated sections)
├── docs/
│   ├── api.md               # Consolidated API reference
│   ├── modules.md           # Module documentation with metrics
│   ├── architecture.md      # Architecture overview with diagrams
│   ├── dependency-graph.md  # Module dependency graphs
│   ├── coverage.md          # Docstring coverage report
│   ├── getting-started.md   # Getting started guide
│   ├── configuration.md    # Configuration reference
│   └── api-changelog.md    # API change tracking
├── examples/
│   ├── quickstart.py       # Basic usage examples
│   └── advanced_usage.py   # Advanced usage examples
├── CONTRIBUTING.md         # Contribution guidelines
└── mkdocs.yml             # MkDocs site configuration
```

## Configuration

Create `prefact.yaml` in your project root (or run `prefact init`):

```yaml
project:
  name: my-project
  source: ./
  output: ./docs/

readme:
  sections:
    - overview
    - install
    - quickstart
    - api
    - structure
  badges:
    - version
    - python
    - coverage
  sync_markers: true

docs:
  api_reference: true
  module_docs: true
  architecture: true
  changelog: true

examples:
  auto_generate: true
  from_entry_points: true

sync:
  strategy: markers    # markers | full | git-diff
  watch: false
  ignore:
    - "tests/"
    - "__pycache__"
```

## Sync Markers

prefact can update only specific sections of an existing README using HTML comment markers:

```markdown
<!-- prefact:start -->
# Project Title
... auto-generated content ...
<!-- prefact:end -->
```

Content outside the markers is preserved when regenerating. Enable this with `sync_markers: true` in your configuration.

## Architecture

```
prefact/
    ├── run_examples        ├── validator        ├── git_hooks        ├── engine    ├── generate_examples        ├── autonomous        ├── fixer    ├── prefact/        ├── config        ├── scanner        ├── models        ├── plugins/            ├── builtin            ├── parallel        ├── performance/            ├── cache        ├── reporters/            ├── console            ├── json_reporter            ├── magic_numbers        ├── config_extended            ├── ruff_based            ├── unused_imports            ├── composite_factory        ├── cli            ├── importchecker_based            ├── registry            ├── type_hints            ├── strategies        ├── rules/            ├── wildcard_imports            ├── pylint_based            ├── ai_boilerplate            ├── string_concat            ├── import_linter_based            ├── isort_based            ├── unimport_based            ├── sorted_imports            ├── llm_generated_code            ├── benchmark            ├── migration            ├── autoflake_based            ├── llm_hallucinations        ├── logging            ├── composite_rules            ├── duplicate_imports            ├── print_statements        ├── messy_module        ├── cli        ├── utils        ├── models        ├── core        ├── sample_code            ├── string_transformations        ├── custom_rules/            ├── mypy_based            ├── after            ├── before            ├── after            ├── before            ├── after            ├── before            ├── after            ├── before            ├── no_todo_rule            ├── after            ├── after            ├── before            ├── before            ├── before            ├── after            ├── after            ├── before├── project    ├── run_all        ├── extension        ├── example            ├── relative_imports```

## API Overview

### Classes

- **`Validator`** — —
- **`GitHooks`** — Manages Git hooks for prefact.
- **`PreCommitConfig`** — Generate pre-commit configuration for prefact.
- **`RefactoringEngine`** — Main entry point: scan the project, apply fixes, validate results.
- **`AutonomousRefact`** — Autonomous prefact manager.
- **`Fixer`** — —
- **`RuleConfig`** — Configuration for a single rule.
- **`Config`** — Top-level configuration.
- **`Scanner`** — Discovers Python files and runs all enabled rules against them.
- **`Severity`** — How critical an issue is.
- **`Phase`** — Pipeline phase.
- **`Issue`** — A single detected problem in the codebase.
- **`Fix`** — A concrete code change to apply.
- **`ValidationResult`** — Result of post-fix validation.
- **`PipelineResult`** — Aggregate result of the full scan → fix → validate pipeline.
- **`PluginMetadata`** — Metadata for a loaded plugin.
- **`PluginValidator`** — Validates plugins before loading.
- **`PluginManager`** — Manages loading and registration of plugins.
- **`ParallelScanTask`** — A task for parallel scanning.
- **`ParallelEngine`** — Parallel processing engine for prefact.
- **`ParallelScanner`** — High-level interface for parallel scanning.
- **`PerformanceMonitor`** — Monitor performance of parallel operations.
- **`Cache`** — Wrapper for diskcache with additional functionality.
- **`ScanResultCache`** — Specialized cache for scan results.
- **`ConfigCache`** — Cache for rule configurations.
- **`RuleResultCache`** — Cache for individual rule results.
- **`FileHashCache`** — Cache for file hashes.
- **`CacheContext`** — Context manager for cache operations.
- **`MagicNumberRule`** — Detect magic numbers in code.
- **`ExtendedConfig`** — Extended configuration with additional features.
- **`ConfigValidator`** — Validate configuration files.
- **`ConfigGenerator`** — Generate configuration files.
- **`RuffHelper`** — Helper class for Ruff operations.
- **`RuffWildcardImports`** — Wildcard imports detection using Ruff.
- **`RuffPrintStatements`** — Print statements detection using Ruff.
- **`RuffUnusedImports`** — Unused imports detection and removal using Ruff.
- **`RuffSortedImports`** — Import sorting using Ruff.
- **`RuffDuplicateImports`** — Duplicate imports detection using Ruff.
- **`UnusedImports`** — —
- **`CompositeRuleFactory`** — Factory for creating composite rules dynamically.
- **`ImportCheckerHelper`** — Helper class for importchecker operations.
- **`ImportCheckerUnusedImports`** — Detect unused imports using importchecker.
- **`ImportCheckerDuplicateImports`** — Detect duplicate imports using importchecker.
- **`ImportDependencyAnalysis`** — Analyze import dependencies using importchecker.
- **`ImportOptimizer`** — Optimize imports based on importchecker analysis.
- **`LazyRuleRegistry`** — Registry that lazily loads rule classes.
- **`MissingReturnType`** — —
- **`ToolStrategy`** — Abstract base class for tool orchestration strategies.
- **`ParallelScanStrategy`** — Run all tools in parallel and merge results.
- **`SequentialScanStrategy`** — Run tools sequentially, passing results between them.
- **`PriorityBasedStrategy`** — Use tool priority to resolve conflicts.
- **`BaseRule`** — Base class every prefactoring rule must implement.
- **`WildcardImports`** — —
- **`PylintHelper`** — Helper class for Pylint operations.
- **`PylintPrintStatements`** — Detect print statements using Pylint.
- **`PylintStringConcat`** — Detect string concatenation using Pylint.
- **`PprefactPylintPlugin`** — Custom Pylint plugin for prefact-specific checks.
- **`PylintComprehensive`** — Comprehensive analysis using Pylint with custom rules.
- **`AIBoilerplateRule`** — Detect AI boilerplate and template code.
- **`StringConcatToFstring`** — —
- **`ImportLinterHelper`** — Helper class for import-linter operations.
- **`ImportLinterLayers`** — Enforce import layering rules using import-linter.
- **`ImportLinterNoRelative`** — Block relative imports using import-linter.
- **`ImportLinterIndependence`** — Ensure module independence using import-linter.
- **`ImportLinterCustomArchitecture`** — Enforce custom architectural rules using import-linter.
- **`ISortHelper`** — Helper class for ISort operations.
- **`ISortedImports`** — Sort imports using ISort.
- **`ImportSectionSeparator`** — Ensure import sections are properly separated.
- **`CustomImportOrganization`** — Organize imports according to custom rules.
- **`UnimportHelper`** — Helper class for unimport operations.
- **`UnimportUnusedImports`** — Remove unused imports using unimport.
- **`UnimportDuplicateImports`** — Remove duplicate imports using unimport.
- **`UnimportStarImports`** — Handle star imports using unimport.
- **`UnimportAll`** — Apply all unimport fixes.
- **`SortedImports`** — —
- **`LLMGeneratedCodeRule`** — Detect code that appears to be LLM-generated.
- **`RuleMigrationManager`** — Manages migration from AST-based rules to Ruff-based rules.
- **`HybridScanner`** — Scanner that can use both AST and Ruff-based rules.
- **`PerformanceProfiler`** — Compare performance between AST and Ruff implementations.
- **`AutoflakeHelper`** — Helper class for Autoflake operations.
- **`AutoflakeUnusedImports`** — Remove unused imports using Autoflake.
- **`AutoflakeUnusedVariables`** — Remove unused variables using Autoflake.
- **`AutoflakeDuplicateKeys`** — Remove duplicate keys in dictionaries using Autoflake.
- **`AutoflakeAll`** — Apply all Autoflake fixes: unused imports, variables, and duplicate keys.
- **`LLMHallucinationRule`** — Detect LLM hallucination patterns in code.
- **`LogLevel`** — Log levels for prefact.
- **`PprefactLogger`** — Structured logger for prefact with enterprise features.
- **`JsonFormatter`** — JSON formatter for structured logging.
- **`PprefactException`** — Base exception for prefact.
- **`ConfigurationError`** — Raised when configuration is invalid.
- **`RuleError`** — Raised when a rule encounters an error.
- **`PluginError`** — Raised when a plugin encounters an error.
- **`CacheError`** — Raised when cache operations fail.
- **`PerformanceError`** — Raised when performance issues are detected.
- **`LogContext`** — Context manager for logging with additional context.
- **`CompositeUnusedImports`** — Composite rule for unused imports using multiple tools.
- **`CompositeImportRules`** — Composite rule for all import-related checks.
- **`CompositeTypeChecking`** — Composite rule for type checking using multiple tools.
- **`DuplicateImports`** — —
- **`PrintStatements`** — —
- **`DataProcessor`** — A class with various issues.
- **`UtilClass`** — Utility class.
- **`User`** — User model.
- **`Post`** — Post model.
- **`DataProcessor`** — A class that processes data.
- **`StringConcatTransformer`** — Transform string concatenations to f-strings.
- **`StringConcatToFString`** — Convert string concatenations to f-strings.
- **`FlyntHelper`** — Helper for using flynt library for string formatting.
- **`FlyntStringFormatting`** — Use flynt library for string formatting optimizations.
- **`ContextAwareStringTransformer`** — Transform string concatenations with context awareness.
- **`ContextAwareStringConcat`** — Context-aware string concatenation to f-string conversion.
- **`MyPyHelper`** — Helper class for MyPy operations.
- **`MyPyMissingReturnType`** — Detect missing return type annotations using MyPy.
- **`MyPyTypeChecking`** — General type checking using MyPy.
- **`ReturnTypeInferrer`** — Infer return types for simple functions.
- **`ReturnTypeAdder`** — Transformer to add return type annotations to functions.
- **`SmartReturnTypeRule`** — Smart return type detection with inference suggestions.
- **`Processor`** — Processor class with absolute imports.
- **`Processor`** — Processor class with relative imports.
- **`Processor`** — Processor class.
- **`Processor`** — Processor class.
- **`NoTodoRule`** — Rule that detects TODO comments in code.
- **`NoPrintRule`** — Custom rule that detects print statements (alternative to built-in).
- **`DataProcessor`** — A class with clean imports.
- **`DataProcessor`** — A class with unused imports.
- **`PrefactIssue`** — —
- **`PrefactResult`** — —
- **`PrefactDiagnosticsProvider`** — —
- **`PrefactTreeItem`** — —
- **`PrefactTreeProvider`** — —
- **`RelativeToAbsoluteImports`** — —

### Functions

- `run_example(example_dir)` — Run a single example and return success status.
- `find_examples(examples_dir)` — Find all example directories with prefact.yaml.
- `main()` — Run all examples and show results.
- `install_git_hooks(repo_root)` — Install Git hooks for the current repository.
- `uninstall_git_hooks(repo_root)` — Uninstall Git hooks for the current repository.
- `list_git_hooks(repo_root)` — List status of Git hooks.
- `main()` — Main CLI for Git hooks management.
- `get_plugin_manager(config)` — Get the global plugin manager instance.
- `register_plugin_rule(plugin_name, version)` — Decorator to register a rule as part of a plugin.
- `init_worker()` — Initialize worker process.
- `scan_file_worker(args)` — Worker function for scanning a single file.
- `get_performance_monitor()` — Get the global performance monitor.
- `initialize_cache(config)` — Initialize the cache system.
- `get_cache()` — Get the global cache instance.
- `get_scan_cache()` — Get the scan result cache.
- `get_config_cache()` — Get the configuration cache.
- `get_rule_cache()` — Get the rule result cache.
- `get_hash_cache()` — Get the file hash cache.
- `cleanup_cache()` — Clean up cache resources.
- `cached_result(expire, key_func)` — Decorator to cache function results.
- `cached_file_operation(expire)` — Decorator to cache file operations.
- `clear_cache(pattern)` — Clear cache entries matching pattern.
- `get_cache_info()` — Get comprehensive cache information.
- `print_report(result)` — —
- `to_dict(result)` — —
- `dump(result)` — —
- `load_config_with_env(config_path, environment)` — Load configuration with environment detection.
- `merge_configs(base, override)` — Merge two configurations.
- `register_composite_rules(config)` — Register composite rules defined in configuration.
- `main(ctx, autonomous, init_only, skip_tests)` — prefact – automatic Python prefactoring toolkit.
- `scan()` — Scan for issues without applying fixes.
- `fix(dry_run, no_backup)` — Scan, fix, and validate in one pass.
- `check(filepath)` — Scan a single file.
- `init(project_path)` — Generate a default prefact.yaml in the project directory.
- `autonomous_cmd(project_path, init_only, skip_tests, skip_examples)` — Run autonomous prefact mode (-a).
- `rules()` — List all available rules.
- `get_lazy_registry()` — Get the global lazy rule registry.
- `get_all_rules()` — Get all rule classes (loads them all).
- `get_rule(rule_id)` — Get a rule class by ID.
- `register(rule_class)` — Decorator to register a rule class.
- `register(cls)` — Decorator that registers a rule class.
- `get_all_rules()` — Get all registered rule classes (loads them all).
- `get_rule(rule_id)` — Get a rule class by ID (loads it if necessary).
- `generate_pylint_rc(config, output_path)` — Generate a .pylintrc file based on prefact configuration.
- `generate_import_linter_config(config, output_path)` — Generate a comprehensive import-linter configuration.
- `benchmark_file(file_path, config)` — Benchmark a single file with both AST and Ruff implementations.
- `benchmark_project(project_root, config)` — Benchmark entire project.
- `print_benchmark_results(results)` — Print formatted benchmark results.
- `main()` — Run benchmark on current project.
- `add_ruff_config_to_prefact_yaml(config_path)` — Add Ruff-specific configuration to prefact.yaml.
- `get_logger()` — Get the global logger instance.
- `setup_logging(config)` — Setup logging from configuration.
- `setup_telemetry(config)` — Setup telemetry callbacks.
- `log_execution(logger)` — Decorator to log function execution.
- `handle_exception(exc_type, exc_value, exc_traceback)` — Handle unhandled exceptions.
- `process_users(users)` — Process user data with multiple issues.
- `generate_report(data)` — Generate a report.
- `main(name, email)` — Main CLI command.
- `admin()` — Admin commands.
- `users()` — List all users.
- `format_name(first, last)` — Format a full name.
- `validate_email(email)` — Validate email address.
- `helper_function(data)` — A helper function without type hints.
- `create_user(name, email)` — Create a new user.
- `load_users_from_file(filepath)` — Load users from JSON file.
- `process_data(data)` — Process some data without return type annotation.
- `calculate_sum(numbers)` — Calculate sum without type hints.
- `process_data(data)` — Process some data.
- `calculate_sum(numbers)` — Calculate sum of numbers.
- `process_user(user_id)` — Process a user.
- `process_user(user_id)` — Process a user.
- `process()` — Process using wildcard imports.
- `process()` — Process using wildcard imports.
- `add(a, b)` — Add two numbers.
- `get_user(user_id)` — Get user by ID.
- `add(a, b)` — Add two numbers.
- `get_user(user_id)` — Get user by ID.
- `process_data()` — Process data.
- `process_data()` — Process data.
- `process_data(data)` — Process some data.
- `format_timestamp(ts)` — Format a timestamp.
- `read_file(filepath)` — Read file contents.
- `greet(name, age)` — Greet someone.
- `format_data(data)` — Format data.
- `greet(name, age)` — Greet someone.
- `format_data(data)` — Format data.
- `process_data(data)` — Process some data.
- `format_timestamp(ts)` — Format a timestamp.
- `read_file(filepath)` — Read file contents.
- `process()` — Process with unsorted imports.
- `process()` — Process with unsorted imports.
- `process_data(data)` — Process data with debug prints.
- `calculate(a, b)` — Calculate with debug output.
- `process_data(data)` — Process data with debug prints.
- `calculate(a, b)` — Calculate with debug output.
- `print_status()` — —
- `print_warning()` — —
- `print_error()` — —
- `run_prefact_example(project_path, config_file, dry_run)` — Run prefact on a project and display results.
- `custom_rule_example()` — Example of using prefact with custom rules.
- `batch_processing_example()` — Example of processing multiple projects.
- `main()` — Main entry point.


## Project Structure

📄 `examples.01-individual-rules.duplicate-imports.after` (1 functions)
📄 `examples.01-individual-rules.duplicate-imports.before` (1 functions)
📄 `examples.01-individual-rules.missing-return-type.after` (3 functions, 1 classes)
📄 `examples.01-individual-rules.missing-return-type.before` (3 functions, 1 classes)
📄 `examples.01-individual-rules.print-statements.after` (2 functions)
📄 `examples.01-individual-rules.print-statements.before` (2 functions)
📄 `examples.01-individual-rules.relative-imports.after` (3 functions, 1 classes)
📄 `examples.01-individual-rules.relative-imports.before` (3 functions, 1 classes)
📄 `examples.01-individual-rules.sorted-imports.after` (1 functions)
📄 `examples.01-individual-rules.sorted-imports.before` (1 functions)
📄 `examples.01-individual-rules.string-concat.after` (2 functions)
📄 `examples.01-individual-rules.string-concat.before` (2 functions)
📄 `examples.01-individual-rules.unused-imports.after` (6 functions, 1 classes)
📄 `examples.01-individual-rules.unused-imports.before` (6 functions, 1 classes)
📄 `examples.01-individual-rules.wildcard-imports.after` (1 functions)
📄 `examples.01-individual-rules.wildcard-imports.before` (1 functions)
📄 `examples.02-multiple-rules.messy_module` (4 functions, 1 classes)
📄 `examples.03-output-formats.sample_code` (2 functions)
📦 `examples.04-custom-rules.custom_rules`
📄 `examples.04-custom-rules.custom_rules.no_todo_rule` (7 functions, 2 classes)
📄 `examples.06-api-usage.example` (4 functions)
📄 `examples.generate_examples`
📄 `examples.run_all` (3 functions)
📄 `examples.run_examples` (3 functions)
📄 `examples.sample-project.cli` (3 functions)
📄 `examples.sample-project.core` (5 functions, 1 classes)
📄 `examples.sample-project.models` (5 functions, 2 classes)
📄 `examples.sample-project.utils` (5 functions, 1 classes)
📄 `project`
📦 `src.prefact`
📄 `src.prefact.autonomous` (15 functions, 1 classes)
📄 `src.prefact.cli` (10 functions)
📄 `src.prefact.config` (13 functions, 2 classes)
📄 `src.prefact.config_extended` (18 functions, 3 classes)
📄 `src.prefact.engine` (4 functions, 1 classes)
📄 `src.prefact.fixer` (2 functions, 1 classes)
📄 `src.prefact.git_hooks` (17 functions, 2 classes)
📄 `src.prefact.logging` (28 functions, 10 classes)
📄 `src.prefact.models` (6 classes)
📦 `src.prefact.performance`
📄 `src.prefact.performance.cache` (37 functions, 6 classes)
📄 `src.prefact.performance.parallel` (23 functions, 4 classes)
📦 `src.prefact.plugins` (17 functions, 3 classes)
📄 `src.prefact.plugins.builtin`
📦 `src.prefact.reporters`
📄 `src.prefact.reporters.console` (1 functions)
📄 `src.prefact.reporters.json_reporter` (2 functions)
📦 `src.prefact.rules` (7 functions, 1 classes)
📄 `src.prefact.rules.ai_boilerplate` (3 functions, 1 classes)
📄 `src.prefact.rules.autoflake_based` (23 functions, 5 classes)
📄 `src.prefact.rules.benchmark` (4 functions)
📄 `src.prefact.rules.composite_factory` (2 functions, 1 classes)
📄 `src.prefact.rules.composite_rules` (16 functions, 3 classes)
📄 `src.prefact.rules.duplicate_imports` (3 functions, 1 classes)
📄 `src.prefact.rules.import_linter_based` (24 functions, 5 classes)
📄 `src.prefact.rules.importchecker_based` (24 functions, 5 classes)
📄 `src.prefact.rules.isort_based` (23 functions, 4 classes)
📄 `src.prefact.rules.llm_generated_code` (9 functions, 1 classes)
📄 `src.prefact.rules.llm_hallucinations` (9 functions, 1 classes)
📄 `src.prefact.rules.magic_numbers` (6 functions, 1 classes)
📄 `src.prefact.rules.migration` (10 functions, 3 classes)
📄 `src.prefact.rules.mypy_based` (22 functions, 6 classes)
📄 `src.prefact.rules.print_statements` (3 functions, 1 classes)
📄 `src.prefact.rules.pylint_based` (22 functions, 5 classes)
📄 `src.prefact.rules.registry` (13 functions, 1 classes)
📄 `src.prefact.rules.relative_imports` (9 functions, 2 classes)
📄 `src.prefact.rules.ruff_based` (19 functions, 6 classes)
📄 `src.prefact.rules.sorted_imports` (4 functions, 1 classes)
📄 `src.prefact.rules.strategies` (10 functions, 4 classes)
📄 `src.prefact.rules.string_concat` (5 functions, 1 classes)
📄 `src.prefact.rules.string_transformations` (27 functions, 6 classes)
📄 `src.prefact.rules.type_hints` (3 functions, 1 classes)
📄 `src.prefact.rules.unimport_based` (22 functions, 5 classes)
📄 `src.prefact.rules.unused_imports` (8 functions, 1 classes)
📄 `src.prefact.rules.wildcard_imports` (3 functions, 1 classes)
📄 `src.prefact.scanner` (6 functions, 1 classes)
📄 `src.prefact.validator` (2 functions, 1 classes)
📄 `vscode-extension.src.extension` (59 functions, 5 classes)

## Requirements

- Python >= >=3.8
- ast-decompiler >=0.7.0- click >=8.0.0- libcst >=0.4.0- pyyaml >=6.0- rich >=12.0.0- tomli >=2.0.0; python_version<'3.11'

## Contributing

**Contributors:**
- Tom Softreck <tom@sapletta.com>
- Tom Sapletta <tom-sapletta-com@users.noreply.github.com>

We welcome contributions! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/semcod/refactoring
cd prefact

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest
```

## Documentation

- 📖 [Full Documentation](https://github.com/semcod/refactoring/tree/main/docs) — API reference, module docs, architecture
- 🚀 [Getting Started](https://github.com/semcod/refactoring/blob/main/docs/getting-started.md) — Quick start guide
- 📚 [API Reference](https://github.com/semcod/refactoring/blob/main/docs/api.md) — Complete API documentation
- 🔧 [Configuration](https://github.com/semcod/refactoring/blob/main/docs/configuration.md) — Configuration options
- 💡 [Examples](./examples) — Usage examples and code samples

### Generated Files

| Output | Description | Link |
|--------|-------------|------|
| `README.md` | Project overview (this file) | — |
| `docs/api.md` | Consolidated API reference | [View](./docs/api.md) |
| `docs/modules.md` | Module reference with metrics | [View](./docs/modules.md) |
| `docs/architecture.md` | Architecture with diagrams | [View](./docs/architecture.md) |
| `docs/dependency-graph.md` | Dependency graphs | [View](./docs/dependency-graph.md) |
| `docs/coverage.md` | Docstring coverage report | [View](./docs/coverage.md) |
| `docs/getting-started.md` | Getting started guide | [View](./docs/getting-started.md) |
| `docs/configuration.md` | Configuration reference | [View](./docs/configuration.md) |
| `docs/api-changelog.md` | API change tracking | [View](./docs/api-changelog.md) |
| `CONTRIBUTING.md` | Contribution guidelines | [View](./CONTRIBUTING.md) |
| `examples/` | Usage examples | [Browse](./examples) |
| `mkdocs.yml` | MkDocs configuration | — |

<!-- code2docs:end -->