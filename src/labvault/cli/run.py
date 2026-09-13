import click
from rich.console import Console

from labvault.core.vault import Vault
from labvault.core.project import get_project
from labvault.core.experiment import get_experiment
from labvault.core.run import create_run, get_run, seal_run
from labvault.core.metrics import add_metrics
from labvault.core.tags import add_tags

console = Console()

def _parse_kv_pairs(pairs: tuple[str, ...]) -> dict[str, str]:
    """Parse KEY=VALUE pairs from CLI arguments."""
    result = {}
    for pair in pairs:
        if "=" not in pair:
            console.print(f"[bold red]Error:[/] Invalid format '{pair}'. Use KEY=VALUE.")
            raise SystemExit(1)
        key, value = pair.split("=", 1)
        result[key.strip()] = value.strip()
    return result

@click.group("run")
def run_group():
    """Manage runs."""
    pass

@run_group.command("start")
@click.argument("project_slug")
@click.argument("exp_slug")
@click.option("--notes", default=None, help="Notes for this run.")
@click.option("--metric", "-m", multiple=True, help="Metric as KEY=VALUE (repeatable).")
@click.option("--tag", "-t", multiple=True, help="Tag as KEY=VALUE (repeatable).")
@click.option("--vault", "vault_path", default=".", help="Path to vault root.")
def run_start(project_slug: str, exp_slug: str, notes: str | None,
              metric: tuple[str, ...], tag: tuple[str, ...], vault_path: str):
    """Start a new run for an experiment."""
    vault = Vault.init(vault_path)
    project = get_project(vault, project_slug)
    if not project:
        console.print(f"[bold red]Error:[/] Project '{project_slug}' not found.")
        raise SystemExit(1)

    experiment = get_experiment(vault, project, exp_slug)
    if not experiment:
        console.print(f"[bold red]Error:[/] Experiment '{exp_slug}' not found in '{project.name}'.")
        raise SystemExit(1)

    tags_dict = _parse_kv_pairs(tag) if tag else None
    metrics_raw = _parse_kv_pairs(metric) if metric else None
    metrics_dict = {k: float(v) for k, v in metrics_raw.items()} if metrics_raw else None

    try:
        run = create_run(vault, experiment, tags=tags_dict, metrics=metrics_dict, notes=notes)
        console.print(
            f"[bold green]Started run:[/] v{run.version} "
            f"[dim]({project.slug}/{experiment.slug}/v{run.version})[/]"
        )
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise SystemExit(1)

@run_group.command("log")
@click.argument("project_slug")
@click.argument("exp_slug")
@click.argument("version", type=int)
@click.option("--metric", "-m", multiple=True, help="Metric as KEY=VALUE (repeatable).")
@click.option("--tag", "-t", multiple=True, help="Tag as KEY=VALUE (repeatable).")
@click.option("--vault", "vault_path", default=".", help="Path to vault root.")
def run_log(project_slug: str, exp_slug: str, version: int,
            metric: tuple[str, ...], tag: tuple[str, ...], vault_path: str):
    """Log metrics and tags to an existing run."""
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

    logged_something = False

    if metric:
        metrics_raw = _parse_kv_pairs(metric)
        metrics_dict = {k: float(v) for k, v in metrics_raw.items()}
        add_metrics(vault, run, metrics_dict)
        for k, v in metrics_dict.items():
            console.print(f"  [cyan]metric[/] {k} = {v}")
        logged_something = True

    if tag:
        tags_dict = _parse_kv_pairs(tag)
        add_tags(vault, run, tags_dict)
        for k, v in tags_dict.items():
            console.print(f"  [yellow]tag[/]    {k} = {v}")
        logged_something = True

    if logged_something:
        # Regenerate _meta.json
        from labvault.core.run import generate_meta_json
        generate_meta_json(vault, experiment, run)
        console.print(f"[bold green]Logged to:[/] v{version}")
    else:
        console.print("[dim]Nothing to log. Use --metric or --tag.[/]")


@run_group.command("seal")
@click.argument("project_slug")
@click.argument("exp_slug")
@click.argument("version", type=int)
@click.option("--vault", "vault_path", default=".", help="Path to vault root.")
def run_seal(project_slug: str, exp_slug: str, version: int, vault_path: str):
    """Seal a run (make it immutable)."""
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
        seal_run(vault, experiment, run)
        console.print(f"[bold green]Sealed:[/] v{version} is now immutable.")
    except ValueError as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise SystemExit(1)


@run_group.command("delete")
@click.argument("project_slug")
@click.argument("exp_slug")
@click.argument("version", type=int)
@click.option("--vault", "vault_path", default=".", help="Path to vault root.")
def run_delete(project_slug: str, exp_slug: str, version: int, vault_path: str):
    """Soft-delete a run (move to trash)."""
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

    from labvault.core.trash import soft_delete_run
    try:
        soft_delete_run(vault, run.id)
        console.print(f"[bold yellow]Trashed:[/] v{version}. Use 'labvault trash ls' to see trashed items.")
    except ValueError as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise SystemExit(1)
