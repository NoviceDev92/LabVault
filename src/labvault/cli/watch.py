"""CLI command for watching a directory and auto-creating runs."""

import time
import click
from pathlib import Path
from rich.console import Console

console = Console()


@click.command("watch")
@click.argument("directory", type=click.Path(exists=True))
@click.argument("project_slug")
@click.argument("exp_slug")
@click.option("--debounce", default=3, type=int, help="Seconds to wait for file writes to settle.")
@click.option("--vault", "vault_path", default=".", help="Path to vault root.")
def watch_cmd(directory: str, project_slug: str, exp_slug: str, debounce: int, vault_path: str):
    """Watch a directory and auto-create runs when new files appear.

    Monitors DIRECTORY for new files and creates runs under the specified
    project and experiment. Files that settle (no writes for DEBOUNCE seconds)
    are automatically ingested as artifacts.
    """
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        console.print("[bold red]Error:[/] The 'watchdog' package is required for this command.")
        console.print("Install it with: [cyan]pip install watchdog[/]")
        raise SystemExit(1)

    from labvault.core.vault import Vault
    from labvault.core.project import get_project
    from labvault.core.experiment import get_experiment
    from labvault.core.run import create_run
    from labvault.core.artifact import add_artifact

    vault = Vault.init(vault_path)
    project = get_project(vault, project_slug)
    if not project:
        console.print(f"[bold red]Error:[/] Project '{project_slug}' not found.")
        raise SystemExit(1)

    experiment = get_experiment(vault, project, exp_slug)
    if not experiment:
        console.print(f"[bold red]Error:[/] Experiment '{exp_slug}' not found.")
        raise SystemExit(1)

    watch_dir = Path(directory).resolve()
    pending: dict[str, float] = {}  # filepath -> last_modified_time

    class RunCreator(FileSystemEventHandler):
        def on_created(self, event):
            if event.is_directory:
                return
            fpath = Path(event.src_path)
            if fpath.name.startswith(".") or fpath.name.startswith("~"):
                return
            pending[str(fpath)] = time.time()

        def on_modified(self, event):
            if event.is_directory:
                return
            fpath = Path(event.src_path)
            if str(fpath) in pending:
                pending[str(fpath)] = time.time()

    handler = RunCreator()
    observer = Observer()
    observer.schedule(handler, str(watch_dir), recursive=False)
    observer.start()

    console.print(f"\n[bold green]👁 Watching:[/] [cyan]{watch_dir}[/]")
    console.print(f"  Project:    [cyan]{project.name}[/]")
    console.print(f"  Experiment: [cyan]{experiment.name}[/]")
    console.print(f"  Debounce:   [cyan]{debounce}s[/]")
    console.print(f"  [dim]Press Ctrl+C to stop.[/]\n")

    try:
        while True:
            time.sleep(1)

            # Check for settled files
            now = time.time()
            settled = [fp for fp, ts in pending.items() if now - ts >= debounce]

            if settled:
                # Create one run for all settled files
                run = create_run(vault, experiment, notes=f"Auto-ingested from {watch_dir.name}")
                console.print(f"[bold green]  ✓ Created run v{run.version}[/]")

                for fp in settled:
                    fpath = Path(fp)
                    if fpath.exists() and fpath.is_file():
                        try:
                            art = add_artifact(vault, run, fpath)
                            console.print(f"    [cyan]→[/] {art.filename} ({art.artifact_type})")
                        except Exception as e:
                            console.print(f"    [red]✕[/] {fpath.name}: {e}")
                    del pending[fp]

                console.print()

    except KeyboardInterrupt:
        observer.stop()
        console.print("\n[dim]Watcher stopped.[/]")

    observer.join()
