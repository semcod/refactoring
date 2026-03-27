#!/usr/bin/env python3
"""Run all prefact examples and verify they work correctly."""

import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, TaskID
from rich.table import Table

console = Console()


def run_example(example_dir: Path) -> Tuple[bool, str]:
    """Run a single example and return success status."""
    config_file = example_dir / "prefact.yaml"
    
    if not config_file.exists():
        return False, f"No prefact.yaml found in {example_dir}"
    
    try:
        # Run prefact scan
        result = subprocess.run(
            [sys.executable, "-m", "prefact.cli", "scan", "--path", str(example_dir), "--config", str(config_file)],
            capture_output=True,
            text=True,
            cwd=example_dir.parent.parent
        )
        
        if result.returncode != 0:
            return False, f"Scan failed: {result.stderr}"
        
        # Run prefact fix if there are issues
        if "issues found" in result.stdout:
            fix_result = subprocess.run(
                [sys.executable, "-m", "prefact.cli", "fix", "--path", str(example_dir), "--config", str(config_file)],
                capture_output=True,
                text=True,
                cwd=example_dir.parent.parent
            )
            
            if fix_result.returncode != 0:
                return False, f"Fix failed: {fix_result.stderr}"
        
        return True, "Success"
        
    except Exception as e:
        return False, f"Error: {e}"


def find_examples(examples_dir: Path) -> List[Path]:
    """Find all example directories with prefact.yaml."""
    examples = []
    
    for item in examples_dir.iterdir():
        if item.is_dir() and (item / "prefact.yaml").exists():
            examples.append(item)
    
    return sorted(examples)


def main():
    """Run all examples and show results."""
    examples_dir = Path(__file__).parent
    
    console.print(Panel.fit("🧪 Running Prefact Examples", style="bold blue"))
    
    # Find all examples
    examples = find_examples(examples_dir)
    
    if not examples:
        console.print("❌ No examples found", style="red")
        return 1
    
    console.print(f"Found {len(examples)} examples")
    
    # Run examples with progress
    results = []
    with Progress() as progress:
        task = progress.add_task("Running examples...", total=len(examples))
        
        for example_dir in examples:
            success, message = run_example(example_dir)
            results.append((example_dir.name, success, message))
            progress.advance(task)
    
    # Show results table
    table = Table(title="Example Results")
    table.add_column("Example", style="bold")
    table.add_column("Status", style="bold")
    table.add_column("Message")
    
    success_count = 0
    for name, success, message in results:
        status = "✅ Passed" if success else "❌ Failed"
        style = "green" if success else "red"
        table.add_row(name, f"[{style}]{status}[/{style}]", message)
        if success:
            success_count += 1
    
    console.print("\n")
    console.print(table)
    
    # Summary
    console.print(f"\nSummary: {success_count}/{len(examples)} examples passed")
    
    if success_count == len(examples):
        console.print("✅ All examples passed!", style="green")
        return 0
    else:
        console.print("❌ Some examples failed", style="red")
        return 1


if __name__ == "__main__":
    sys.exit(main())
