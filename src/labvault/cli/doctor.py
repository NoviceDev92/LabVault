"""CLI command for vault integrity checking."""

import click
from rich.console import Console

from labvault.core.vault import Vault
from labvault.core.doctor import check_integrity

console = Console()


@click.command("doctor")
@click.option("--vault", "vault_path", default=".", help="Path to vault root.")
def doctor_cmd(vault_path: str):
    """Check vault integrity — verify DB ↔ filesystem consistency."""
    vault = Vault.init(vault_path)
    console.print("\n[bold]🩺 LabVault Doctor[/]  —  Running integrity checks...\n")

    report = check_integrity(vault)

    console.print(f"  Artifacts scanned: [cyan]{report.total_artifacts_checked}[/]")
    console.print()

    if report.orphaned_db_records:
        console.print(f"  [bold red]✕ DB Records Missing on Disk ({len(report.orphaned_db_records)}):[/]")
        for item in report.orphaned_db_records:
            console.print(f"    [red]•[/red] {item}")
        console.print()

    if report.orphaned_files:
        console.print(f"  [bold yellow]⚠ Files on Disk Not in DB ({len(report.orphaned_files)}):[/]")
        for item in report.orphaned_files:
            console.print(f"    [yellow]•[/yellow] {item}")
        console.print()

    if report.hash_mismatches:
        console.print(f"  [bold red]✕ Hash Mismatches ({len(report.hash_mismatches)}):[/]")
        for item in report.hash_mismatches:
            console.print(f"    [red]•[/red] {item}")
        console.print()

    if report.missing_meta:
        console.print(f"  [bold yellow]⚠ Missing _meta.json ({len(report.missing_meta)}):[/]")
        for item in report.missing_meta:
            console.print(f"    [yellow]•[/yellow] {item}")
        console.print()

    if report.is_healthy:
        console.print("  [bold green]✓ Vault is healthy.[/] No issues found.\n")
    else:
        total_issues = (
            len(report.orphaned_db_records)
            + len(report.orphaned_files)
            + len(report.hash_mismatches)
            + len(report.missing_meta)
        )
        console.print(f"  [bold red]Found {total_issues} issue(s).[/]\n")
