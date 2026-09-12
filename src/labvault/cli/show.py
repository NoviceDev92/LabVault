import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from labvault.core.vault import Vault
from labvault.core.project import get_project
from labvault.core.experiment import get_experiment
from labvault.core.run import list_runs
from labvault.core.metrics import get_metrics
from labvault.core.tags import get_tags
from labvault.core.artifact import list_artifacts
from labvault.utils.filesize import format_bytes

console = Console()

@click.command("show")
@click.argument("project_slug")
@click.argument("exp_slug")
@click.option("--vault", "vault_path", default=".", help="Path to vault root.")
def show(project_slug: str, exp_slug: str, vault_path: str):
    """Show a detailed summary of all runs in an experiment."""
    vault = Vault.init(vault_path)
    project = get_project(vault, project_slug)
    if not project:
        console.print(f"[bold red]Error:[/] Project '{project_slug}' not found.")
        raise SystemExit(1)

    experiment = get_experiment(vault, project, exp_slug)
    if not experiment:
        console.print(f"[bold red]Error:[/] Experiment '{exp_slug}' not found.")
        raise SystemExit(1)

    runs = list_runs(vault, experiment)

    if not runs:
        console.print(f"[dim]No runs in '{experiment.name}'. Create one with:[/] labvault run start {project_slug} {exp_slug}")
        return

    # Collect all unique metric keys across runs for dynamic columns
    all_metric_keys: set[str] = set()
    runs_data = []
    for run in runs:
        metrics = get_metrics(vault, run)
        tags = get_tags(vault, run)
        artifacts = list_artifacts(vault, run)
        all_metric_keys.update(metrics.keys())
        runs_data.append((run, metrics, tags, artifacts))

    sorted_metric_keys = sorted(all_metric_keys)

    # Build table
    table = Table(
        title=f"[bold]{project.name}[/] / [cyan]{experiment.name}[/]",
        show_lines=True,
        title_style="bold",
    )
    table.add_column("Version", style="bold green", justify="center")
    table.add_column("Status", justify="center")
    for mk in sorted_metric_keys:
        table.add_column(mk, style="cyan", justify="right")
    table.add_column("Tags", style="yellow")
    table.add_column("Artifacts", style="dim")
    table.add_column("Created", style="dim")

    for run, metrics, tags, artifacts in runs_data:
        status_style = "green" if run.status == "sealed" else "yellow"
        status_text = f"[{status_style}]{run.status}[/{status_style}]"

        metric_values = [f"{metrics.get(mk, '-')}" for mk in sorted_metric_keys]

        tag_str = ", ".join(f"{k}={v}" for k, v in tags.items()) if tags else "-"

        artifact_summary = []
        for a in artifacts:
            artifact_summary.append(f"{a.filename} ({format_bytes(a.size_bytes)})")
        artifact_str = "\n".join(artifact_summary) if artifact_summary else "-"

        created = run.created_at[:19] if run.created_at else "-"

        table.add_row(
            f"v{run.version}",
            status_text,
            *metric_values,
            tag_str,
            artifact_str,
            created,
        )

    console.print(table)
