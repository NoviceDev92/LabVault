import click
from pathlib import Path
from rich.console import Console

from labvault.core.vault import Vault
from labvault.core.project import get_project
from labvault.core.experiment import get_experiment
from labvault.core.run import get_run
from labvault.core.artifact import add_artifact, extract_metrics_from_file

console = Console()

@click.group("artifact")
def artifact_group():
    """Manage artifacts."""
    pass

@artifact_group.command("add")
@click.argument("project_slug")
@click.argument("exp_slug")
@click.argument("version", type=int)
@click.argument("filepath", type=click.Path(exists=True))
@click.option("--type", "artifact_type", default=None, help="Override auto-detected artifact type.")
@click.option("--auto-metrics", is_flag=True, default=False, help="Auto-extract metrics from .json/.csv files.")
@click.option("--vault", "vault_path", default=".", help="Path to vault root.")
def artifact_add(project_slug: str, exp_slug: str, version: int,
                 filepath: str, artifact_type: str | None, auto_metrics: bool,
                 vault_path: str):
    """Add a file artifact to a run."""
    vault = Vault.init(vault_path)
    project = get_project(vault, project_slug)
    if not project:
        console.print(f"[bold red]Error:[/] Project '{project_slug}' not found.")
        raise SystemExit(1)

    experiment = get_experiment(vault, project, exp_slug)
    if not experiment:
        console.print(f"[bold red]Error:[/] Experiment '{exp_slug}' not found.")
        raise SystemExit(1)

    run = get_run(vault, experiment, version)
    if not run:
        console.print(f"[bold red]Error:[/] Run v{version} not found.")
        raise SystemExit(1)

    try:
        art = add_artifact(vault, run, Path(filepath), artifact_type=artifact_type)
        from labvault.utils.filesize import format_bytes
        console.print(
            f"[bold green]Added artifact:[/] {art.filename} "
            f"[dim]({art.artifact_type}, {format_bytes(art.size_bytes)})[/]"
        )

        # Auto-extract metrics if requested
        if auto_metrics:
            metrics = extract_metrics_from_file(Path(filepath))
            if metrics:
                from labvault.core.metrics import add_metrics
                add_metrics(vault, run, metrics)
                for k, v in metrics.items():
                    console.print(f"  [cyan]auto-metric[/] {k} = {v}")
                console.print(f"[bold green]Extracted {len(metrics)} metric(s)[/]")
            else:
                console.print("[dim]No extractable metrics found in this file.[/]")

    except FileNotFoundError as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise SystemExit(1)

