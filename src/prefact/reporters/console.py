"""Rich-based console reporter for pipeline results."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from prefact.models import PipelineResult, Severity

_STYLE = {
    Severity.INFO: "cyan",
    Severity.WARNING: "yellow",
    Severity.ERROR: "bold red",
}


def print_report(result: PipelineResult, *, verbose: bool = False) -> None:
    console = Console()

    mode = "[dim](dry-run)[/]" if result.dry_run else ""
    console.print()
    console.print(Panel(f"[bold]prefact Report[/bold] {mode}", border_style="blue", expand=False))

    if result.issues_found:
        table = Table(title="Issues Found", show_lines=False)
        table.add_column("Location", style="dim")
        table.add_column("Rule", style="bold")
        table.add_column("Sev")
        table.add_column("Message")
        for iss in result.issues_found:
            s = _STYLE.get(iss.severity, "white")
            table.add_row(iss.location, iss.rule_id, f"[{s}]{iss.severity.value}[/]", iss.message)
        console.print(table)
    else:
        console.print("[green]✓ No issues found.[/green]")

    if result.fixes_applied:
        console.print(f"\n[green]✓ Applied {result.total_fixed} fix(es).[/green]")
        if verbose:
            for fix in result.fixes_applied:
                console.print(f"  [dim]{fix.file}[/dim] — {fix.original_code} → {fix.fixed_code}")

    if result.fixes_failed:
        console.print(f"\n[red]✗ {result.total_failed} fix(es) failed.[/red]")
        for fix in result.fixes_failed:
            console.print(f"  [red]{fix.file}: {fix.error}[/red]")

    if result.validations:
        if result.all_valid:
            console.print("[green]✓ All validations passed.[/green]")
        else:
            console.print("[red]✗ Some validations failed:[/red]")
            for v in result.validations:
                if not v.passed:
                    for err in v.errors:
                        console.print(f"  [red]{v.file}: {err}[/red]")

    console.print()
    parts = [
        f"[bold]{result.total_issues}[/bold] issue(s)",
        f"[green]{result.total_fixed}[/green] fixed",
        f"[red]{result.total_failed}[/red] failed",
    ]
    console.print(" │ ".join(parts))
    console.print()
