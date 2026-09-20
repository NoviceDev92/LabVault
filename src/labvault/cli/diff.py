"""CLI command for side-by-side run comparison with color-coded deltas."""

import click
from rich.console import Console
from rich.table import Table

from labvault.core.vault import Vault
from labvault.core.project import get_project
from labvault.core.experiment import get_experiment
from labvault.core.run import get_run
from labvault.core.comparison import compare_runs

console = Console()


@click.command("diff")
@click.argument("project_slug")
@click.argument("exp_slug")
@click.argument("v1", type=int)
@click.argument("v2", type=int)
@click.option("--vault", "vault_path", default=".", help="Path to vault root.")
def diff_cmd(project_slug: str, exp_slug: str, v1: int, v2: int, vault_path: str):
    """Compare two runs side-by-side with color-coded deltas."""
    vault = Vault.init(vault_path)

    project = get_project(vault, project_slug)
    if not project:
        console.print(f"[bold red]Error:[/] Project '{project_slug}' not found.")
        raise SystemExit(1)

    experiment = get_experiment(vault, project, exp_slug)
    if not experiment:
        console.print(f"[bold red]Error:[/] Experiment '{exp_slug}' not found.")
        raise SystemExit(1)

    run_a = get_run(vault, experiment, v1)
    run_b = get_run(vault, experiment, v2)
    if not run_a:
        console.print(f"[bold red]Error:[/] Run v{v1} not found.")
        raise SystemExit(1)
    if not run_b:
        console.print(f"[bold red]Error:[/] Run v{v2} not found.")
        raise SystemExit(1)

    result = compare_runs(vault, [run_a.id, run_b.id])

    console.print()
    console.print(f"[bold]Comparing[/] [cyan]v{v1}[/] ↔ [cyan]v{v2}[/] in [bold]{experiment.name}[/]")
    console.print()

    # Metrics table
    if result.metric_deltas:
        table = Table(title="Metric Deltas", border_style="dim", show_lines=True)
        table.add_column("Metric", style="bold")
        table.add_column(f"v{v1}", justify="right", style="cyan")
        table.add_column(f"v{v2}", justify="right", style="cyan")
        table.add_column("Delta", justify="right")

        for md in result.metric_deltas:
            val_a = md.values.get(run_a.id)
            val_b = md.values.get(run_b.id)
            a_str = f"{val_a}" if val_a is not None else "—"
            b_str = f"{val_b}" if val_b is not None else "—"

            delta_str = ""
            if val_a is not None and val_b is not None and val_a != 0:
                diff = val_b - val_a
                pct = (diff / abs(val_a)) * 100
                sign = "+" if diff > 0 else ""

                is_loss = "loss" in md.key.lower()
                is_good = (diff < 0) if is_loss else (diff > 0)

                color = "green" if is_good else "red"
                delta_str = f"[{color}]{sign}{pct:.1f}%[/{color}]"

            table.add_row(md.key, a_str, b_str, delta_str)

        console.print(table)
        console.print()

    # Tags table
    if result.tag_diffs:
        table = Table(title="Tag Differences", border_style="dim", show_lines=True)
        table.add_column("Tag", style="bold")
        table.add_column(f"v{v1}", style="cyan")
        table.add_column(f"v{v2}", style="cyan")
        table.add_column("Status")

        for td in result.tag_diffs:
            val_a = td.values.get(run_a.id, "—")
            val_b = td.values.get(run_b.id, "—")
            status = "[dim]same[/dim]" if td.is_uniform else "[yellow]DIFF[/yellow]"
            table.add_row(td.key, val_a, val_b, status)

        console.print(table)
        console.print()

    # Artifacts table
    if result.artifact_diffs:
        table = Table(title="Artifact Comparison", border_style="dim", show_lines=True)
        table.add_column("File", style="bold")
        table.add_column(f"v{v1}")
        table.add_column(f"v{v2}")

        for ad in result.artifact_diffs:
            in_a = run_a.id in ad.present_in
            in_b = run_b.id in ad.present_in
            a_str = f"[green]✓[/green] {_fmt_size(ad.sizes.get(run_a.id))}" if in_a else "[dim]—[/dim]"
            b_str = f"[green]✓[/green] {_fmt_size(ad.sizes.get(run_b.id))}" if in_b else "[dim]—[/dim]"
            table.add_row(ad.filename, a_str, b_str)

        console.print(table)


def _fmt_size(size_bytes):
    if size_bytes is None:
        return ""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
