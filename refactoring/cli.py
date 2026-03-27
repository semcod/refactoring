"""
Command line interface for the refactoring package.
"""

import click
import sys
from pathlib import Path

from .core import RefactoringEngine
from .utils import parse_code, analyze_structure, get_file_stats


@click.group()
@click.version_option()
def main():
    """Refactoring tools for Python code analysis and transformation."""
    pass


@main.command()
@click.argument('file_path', type=click.Path(exists=True))
def analyze(file_path):
    """Analyze a Python file and display its structure."""
    engine = RefactoringEngine()
    
    # Parse the file
    parsed = parse_code(file_path)
    if not parsed["success"]:
        click.echo(f"Error parsing file: {parsed['error']}", err=True)
        sys.exit(1)
    
    # Analyze the code
    analysis = engine.analyze_code(parsed["code"])
    if not analysis["success"]:
        click.echo(f"Error analyzing code: {analysis['error']}", err=True)
        sys.exit(1)
    
    # Display results
    click.echo(f"\n📁 File: {file_path}")
    click.echo("=" * 50)
    
    click.echo(f"\n📊 Functions ({len(analysis['functions'])}):")
    for func in analysis['functions']:
        click.echo(f"  • {func['name']} (line {func['line']}) - {len(func['args'])} args")
    
    click.echo(f"\n🏗️  Classes ({len(analysis['classes'])}):")
    for cls in analysis['classes']:
        click.echo(f"  • {cls['name']} (line {cls['line']}) - {len(cls['methods'])} methods")
    
    click.echo(f"\n📦 Imports ({len(analysis['imports'])}):")
    for imp in analysis['imports']:
        if imp['type'] == 'import':
            alias = f" as {imp['alias']}" if imp['alias'] else ""
            click.echo(f"  • import {imp['module']}{alias}")
        else:
            name = f" as {imp['alias']}" if imp['alias'] else imp['name']
            click.echo(f"  • from {imp['module']} import {name}")


@main.command()
@click.argument('file_path', type=click.Path(exists=True))
def stats(file_path):
    """Display statistics about a Python file."""
    stats_data = get_file_stats(file_path)
    
    if not stats_data["success"]:
        click.echo(f"Error getting stats: {stats_data['error']}", err=True)
        sys.exit(1)
    
    click.echo(f"\n📊 Statistics for: {file_path}")
    click.echo("=" * 40)
    click.echo(f"Total lines: {stats_data['total_lines']}")
    click.echo(f"Code lines: {stats_data['code_lines']}")
    click.echo(f"Comment lines: {stats_data['comment_lines']}")
    click.echo(f"Blank lines: {stats_data['blank_lines']}")
    click.echo(f"Functions: {stats_data['functions']}")
    click.echo(f"Classes: {stats_data['classes']}")
    click.echo(f"Cyclomatic complexity: {stats_data['complexity']}")


@main.command()
@click.argument('directory', type=click.Path(exists=True, file_okay=False))
@click.option('--recursive', '-r', is_flag=True, help='Search recursively')
def scan(directory):
    """Scan directory for Python files and show basic info."""
    path = Path(directory)
    
    if recursive:
        py_files = list(path.rglob('*.py'))
    else:
        py_files = list(path.glob('*.py'))
    
    if not py_files:
        click.echo("No Python files found.")
        return
    
    click.echo(f"\n🔍 Found {len(py_files)} Python files:")
    click.echo("=" * 50)
    
    total_lines = 0
    total_functions = 0
    total_classes = 0
    
    for file_path in sorted(py_files):
        stats_data = get_file_stats(str(file_path))
        if stats_data["success"]:
            click.echo(f"📄 {file_path.relative_to(path)}")
            click.echo(f"   Lines: {stats_data['total_lines']}, Functions: {stats_data['functions']}, Classes: {stats_data['classes']}")
            total_lines += stats_data['total_lines']
            total_functions += stats_data['functions']
            total_classes += stats_data['classes']
    
    click.echo(f"\n📈 Summary:")
    click.echo(f"Total files: {len(py_files)}")
    click.echo(f"Total lines: {total_lines}")
    click.echo(f"Total functions: {total_functions}")
    click.echo(f"Total classes: {total_classes}")


if __name__ == '__main__':
    main()
