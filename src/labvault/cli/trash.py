import click
from rich.console import Console
from rich.table import Table

from labvault.core.vault import Vault
from labvault.core.trash import list_trash, restore_from_trash

console = Console()


@click.group("trash")
def trash_group():
    """Manage trashed runs."""
    pass


@trash_group.command("ls")
@click.option("--vault", "vault_path", default=".", help="Path to vault root.")
def trash_ls(vault_path: str):
    """List all trashed runs."""
    vault = Vault.init(vault_path)
    items = list_trash(vault)

    if not items:
        console.print("[dim]Trash is empty.[/]")
        return

    table = Table(title="Trash", show_lines=True)
    table.add_column("Trash ID", style="dim", justify="right")
    table.add_column("Project", style="cyan")
    table.add_column("Experiment", style="bold")
    table.add_column("Version", style="green", justify="center")
    table.add_column("Deleted At", style="red")

    for item in items:
        table.add_row(
            str(item.id),
            item.project_name or f"(id:{item.project_id})",
            item.experiment_name or f"(id:{item.experiment_id})",
            f"v{item.version}",
            item.deleted_at[:19] if item.deleted_at else "-",
        )

    console.print(table)


@trash_group.command("restore")
@click.argument("trash_id", type=int)
@click.option("--vault", "vault_path", default=".", help="Path to vault root.")
def trash_restore(trash_id: int, vault_path: str):
    """Restore a trashed run."""
    vault = Vault.init(vault_path)
    try:
        item = restore_from_trash(vault, trash_id)
        console.print(
            f"[bold green]Restored:[/] v{item.version} back to its original location."
        )
    except ValueError as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise SystemExit(1)
