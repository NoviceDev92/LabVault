"""CLI command for viewing and modifying LabVault configuration."""

import click
from rich.console import Console
from rich.table import Table

from labvault.core.config import load_config, set_config_value, get_config_value, _config_path

console = Console()


@click.command("config")
@click.option("--set", "set_pair", default=None, help="Set a config value (KEY=VALUE, e.g. ui.port=8080).")
@click.option("--get", "get_key", default=None, help="Get a specific config value (e.g. ui.port).")
@click.option("--show", is_flag=True, help="Show all config values.")
def config_cmd(set_pair: str | None, get_key: str | None, show: bool):
    """View or modify LabVault configuration."""
    if set_pair:
        if "=" not in set_pair:
            console.print("[bold red]Error:[/] Use KEY=VALUE format (e.g. --set ui.port=8080).")
            raise SystemExit(1)

        key, value = set_pair.split("=", 1)
        set_config_value(key.strip(), value.strip())
        console.print(f"[bold green]✓[/] Set [cyan]{key.strip()}[/] = [yellow]{value.strip()}[/]")
        console.print(f"[dim]Config saved to {_config_path()}[/]")
        return

    if get_key:
        val = get_config_value(get_key)
        if val is None:
            console.print(f"[dim]{get_key}[/] is not set (or null).")
        else:
            console.print(f"[cyan]{get_key}[/] = [yellow]{val}[/]")
        return

    # Default: --show
    cfg = load_config()
    console.print(f"\n[bold]LabVault Configuration[/]  [dim]({_config_path()})[/]\n")

    table = Table(border_style="dim", show_lines=True)
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="yellow")

    def _flatten(d, prefix=""):
        for k, v in d.items():
            full_key = f"{prefix}{k}" if not prefix else f"{prefix}.{k}"
            if isinstance(v, dict):
                _flatten(v, full_key)
            else:
                table.add_row(full_key if not prefix else full_key, str(v) if v is not None else "[dim]null[/dim]")

    _flatten(cfg)
    console.print(table)
