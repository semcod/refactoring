"""Command-line interface for prefact."""

from __future__ import annotations

from pathlib import Path

import click

from prefact.config import Config
from prefact.engine import RefactoringEngine
from prefact.reporters import console as console_reporter
from prefact.reporters import json_reporter


@click.group()
@click.version_option(package_name="prefact")
def main() -> None:
    """prefact – automatic Python refactoring toolkit.

    Detect, fix, and validate common code issues – especially those
    introduced by LLMs (e.g. relative imports, unused imports).
    """


# ── shared options ────────────────────────────────────────────────────


def _common_options(fn):
    fn = click.option("-p", "--path", "project_path", default=".", help="Project root directory.")(fn)
    fn = click.option("--package", "package_name", default="", help="Package name (auto-detected if omitted).")(fn)
    fn = click.option("-c", "--config", "config_file", default=None, help="Path to prefact.yaml config.")(fn)
    fn = click.option("--verbose", is_flag=True, help="Show detailed output.")(fn)
    fn = click.option("--format", "output_format", type=click.Choice(["console", "json"]), default="console")(fn)
    fn = click.option("-o", "--output", "output_file", default=None, help="Write JSON report to file.")(fn)
    return fn


def _build_config(project_path, package_name, config_file, verbose, **_kw) -> Config:
    if config_file:
        cfg = Config.from_yaml(Path(config_file))
    else:
        # Auto-discover prefact.yaml
        candidate = Path(project_path).resolve() / "prefact.yaml"
        if candidate.exists():
            cfg = Config.from_yaml(candidate)
        else:
            cfg = Config()
    cfg.project_root = Path(project_path).resolve()
    if package_name:
        cfg.package_name = package_name
    cfg.verbose = verbose
    return cfg


# ── commands ──────────────────────────────────────────────────────────


@main.command()
@_common_options
def scan(**kwargs) -> None:
    """Scan for issues without applying fixes."""
    cfg = _build_config(**kwargs)
    engine = RefactoringEngine(cfg)
    result = engine.scan_only()
    _output(result, kwargs)


@main.command()
@_common_options
@click.option("--dry-run", is_flag=True, help="Show what would change without writing files.")
@click.option("--no-backup", is_flag=True, help="Don't create .bak backup files.")
def fix(dry_run, no_backup, **kwargs) -> None:
    """Scan, fix, and validate in one pass."""
    cfg = _build_config(**kwargs)
    cfg.dry_run = dry_run
    cfg.backup = not no_backup
    engine = RefactoringEngine(cfg)
    result = engine.run()
    _output(result, kwargs)
    if not result.all_valid:
        raise SystemExit(1)


@main.command()
@_common_options
@click.argument("filepath")
def check(filepath, **kwargs) -> None:
    """Scan a single file."""
    cfg = _build_config(**kwargs)
    engine = RefactoringEngine(cfg)
    result = engine.run_file(Path(filepath), dry_run=True)
    _output(result, kwargs)


@main.command()
@click.option("-p", "--path", "project_path", default=".", help="Where to create prefact.yaml.")
def init(project_path) -> None:
    """Generate a default prefact.yaml in the project directory."""
    default = """\
# prefact.yaml – configuration for prefact
# package_name: mypackage     # auto-detected from pyproject.toml if omitted

include:
  - "**/*.py"

exclude:
  - "**/__pycache__/**"
  - "**/venv/**"
  - "**/.venv/**"
  - "**/build/**"
  - "**/dist/**"

rules:
  relative-imports:
    enabled: true
    severity: warning
  unused-imports:
    enabled: true
    severity: info
  duplicate-imports:
    enabled: true
    severity: warning
  wildcard-imports:
    enabled: true
    severity: error
  sorted-imports:
    enabled: false
    severity: info
  string-concat:
    enabled: true
    severity: info
  print-statements:
    enabled: true
    severity: info
    options:
      ignore_patterns: ["cli.py", "scripts/"]
  missing-return-type:
    enabled: false
    severity: info
"""
    dest = Path(project_path).resolve() / "prefact.yaml"
    if dest.exists():
        click.echo(f"File already exists: {dest}")
        raise SystemExit(1)
    dest.write_text(default)
    click.echo(f"Created {dest}")


@main.command()
def rules() -> None:
    """List all available rules."""
    from prefact.rules import get_all_rules

    from rich.console import Console
    from rich.table import Table

    console = Console()
    table = Table(title="Available Rules")
    table.add_column("Rule ID", style="bold")
    table.add_column("Description")
    table.add_column("Auto-fix")
    for rule_id, rule_cls in sorted(get_all_rules().items()):
        # Heuristic: if fix() returns source unchanged, it's scan-only
        has_fix = rule_id in ("relative-imports", "unused-imports", "duplicate-imports")
        table.add_row(rule_id, rule_cls.description, "✅" if has_fix else "🔍 scan-only")
    console.print(table)


# ── helpers ───────────────────────────────────────────────────────────


def _output(result, kwargs) -> None:
    fmt = kwargs.get("output_format", "console")
    if fmt == "json":
        text = json_reporter.dump(
            result,
            output=Path(kwargs["output_file"]) if kwargs.get("output_file") else None,
        )
        if not kwargs.get("output_file"):
            click.echo(text)
    else:
        console_reporter.print_report(result, verbose=kwargs.get("verbose", False))


if __name__ == "__main__":
    main()
