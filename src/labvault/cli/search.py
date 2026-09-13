import click
from rich.console import Console
from rich.table import Table

from labvault.core.vault import Vault
from labvault.core.search import search

console = Console()


@click.command("search")
@click.argument("query", required=False, default=None)
@click.option("--tag", "-t", multiple=True, help="Tag filter as KEY=VALUE (repeatable).")
@click.option("--metric", "-m", multiple=True, help='Metric filter like "f1 > 0.9" (repeatable).')
@click.option("--after", default=None, help="Only runs created after this date (YYYY-MM-DD).")
@click.option("--before", default=None, help="Only runs created before this date (YYYY-MM-DD).")
@click.option("--vault", "vault_path", default=".", help="Path to vault root.")
def search_cmd(query, tag, metric, after, before, vault_path):
    """Search runs by text, tags, or metric ranges."""
    vault = Vault.init(vault_path)

    tag_filters = list(tag) if tag else None
    metric_filters = list(metric) if metric else None

    try:
        results = search(vault, query=query, tag_filters=tag_filters,
                         metric_filters=metric_filters, after=after, before=before)
    except ValueError as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise SystemExit(1)

    if not results:
        console.print("[dim]No results found.[/]")
        return

    table = Table(title="Search Results", show_lines=True)
    table.add_column("Project", style="cyan")
    table.add_column("Experiment", style="bold")
    table.add_column("Version", style="green", justify="center")
    table.add_column("Metrics", style="dim")
    table.add_column("Tags", style="yellow")
    table.add_column("Notes")

    for r in results:
        metrics_str = ", ".join(f"{k}={v}" for k, v in r.metrics.items()) if r.metrics else "-"
        tags_str = ", ".join(f"{k}={v}" for k, v in r.tags.items()) if r.tags else "-"
        table.add_row(
            r.project_name,
            r.experiment_name,
            f"v{r.version}",
            metrics_str,
            tags_str,
            r.notes or "-",
        )

    console.print(table)
