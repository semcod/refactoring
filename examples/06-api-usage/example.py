#!/usr/bin/env python3
"""Example of using prefact programmatically."""

import argparse
import json
from pathlib import Path
from typing import Dict, Any

from prefact.config import Config
from prefact.engine import RefactoringEngine


def run_prefact_example(project_path: Path, config_file: Path = None, dry_run: bool = False):
    """Run prefact on a project and display results."""
    
    # Create configuration
    if config_file and config_file.exists():
        print(f"Loading config from {config_file}")
        config = Config.from_yaml(config_file)
    else:
        print("Using default configuration")
        config = Config()
    
    # Override project path
    config.project_root = project_path.resolve()
    
    # Set dry run mode
    config.dry_run = dry_run
    
    # Create and run engine
    print(f"\n🔍 Scanning {project_path}")
    print(f"Package: {config.package_name or 'auto-detect'}")
    print(f"Dry run: {dry_run}")
    print("-" * 50)
    
    engine = RefactoringEngine(config)
    result = engine.run()
    
    # Display results
    print(f"\n📊 Results:")
    print(f"  Files scanned: {result.files_scanned}")
    print(f"  Total issues: {result.total_issues}")
    print(f"  Issues fixed: {result.total_fixed}")
    print(f"  Validation passed: {result.all_valid}")
    
    # Show issues by rule
    if result.issues_by_rule:
        print(f"\n📋 Issues by rule:")
        for rule_id, issues in result.issues_by_rule.items():
            print(f"  {rule_id}: {len(issues)} issues")
    
    # Show fix details
    if result.fixes:
        print(f"\n🔧 Fixes applied:")
        for fix in result.fixes[:5]:  # Show first 5
            print(f"  {fix.path}:{fix.line} - {fix.description}")
        if len(result.fixes) > 5:
            print(f"  ... and {len(result.fixes) - 5} more")
    
    # Show validation failures
    if result.validation_failures:
        print(f"\n❌ Validation failures:")
        for failure in result.validation_failures:
            print(f"  {failure.path}: {failure.message}")
    
    return result


def custom_rule_example():
    """Example of using prefact with custom rules."""
    print("\n" + "=" * 50)
    print("CUSTOM RULE EXAMPLE")
    print("=" * 50)
    
    # Create a temporary project with custom rules
    temp_dir = Path("temp_custom_project")
    temp_dir.mkdir(exist_ok=True)
    
    # Create a file with TODO comments
    test_file = temp_dir / "test.py"
    test_file.write_text("""
# TODO: Implement this function
def incomplete_function():
    pass

# TODO: Add error handling
# TODO: Write tests
def another_function():
    print("debug")
""")
    
    # Create config with custom rules
    config = Config()
    config.project_root = temp_dir.resolve()
    config.package_name = "temp_project"
    
    # Import custom rules
    try:
        from examples.custom_rules.no_todo_rule import NoTodoRule
        print("✅ Custom rules loaded")
    except ImportError:
        print("⚠️ Could not load custom rules")
        return
    
    # Run with custom rules
    engine = RefactoringEngine(config)
    result = engine.run()
    
    print(f"\nCustom rule results:")
    print(f"  TODO comments found: {len([i for i in result.all_issues if 'todo' in i.rule_id])}")
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)


def batch_processing_example():
    """Example of processing multiple projects."""
    print("\n" + "=" * 50)
    print("BATCH PROCESSING EXAMPLE")
    print("=" * 50)
    
    # List of projects to process
    projects = [
        Path("../sample-project"),
        Path("../01-individual-rules/relative-imports"),
        Path("../02-multiple-rules"),
    ]
    
    results = []
    
    for project in projects:
        if project.exists():
            print(f"\nProcessing {project.name}...")
            config = Config()
            config.project_root = project.resolve()
            config.dry_run = True  # Don't actually fix
            
            engine = RefactoringEngine(config)
            result = engine.run()
            
            results.append({
                "project": project.name,
                "issues": result.total_issues,
                "fixable": len([i for i in result.all_issues if i.fixable])
            })
        else:
            print(f"⚠️ Project {project} not found")
    
    # Summary table
    print(f"\n📊 Batch Summary:")
    print(f"{'Project':<30} {'Issues':<10} {'Fixable':<10}")
    print("-" * 50)
    for r in results:
        print(f"{r['project']:<30} {r['issues']:<10} {r['fixable']:<10}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="prefact API Usage Example")
    parser.add_argument("--path", type=Path, default=Path("."), help="Project path to scan")
    parser.add_argument("--config", type=Path, help="Configuration file")
    parser.add_argument("--dry-run", action="store_true", help="Don't apply fixes")
    parser.add_argument("--custom-rules", action="store_true", help="Run custom rule example")
    parser.add_argument("--batch", action="store_true", help="Run batch processing example")
    
    args = parser.parse_args()
    
    # Main example
    result = run_prefact_example(args.path, args.config, args.dry_run)
    
    # Additional examples
    if args.custom_rules:
        custom_rule_example()
    
    if args.batch:
        batch_processing_example()
    
    # Return exit code based on results
    return 1 if result.total_issues > 0 else 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
