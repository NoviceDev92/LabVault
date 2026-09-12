import os
from pathlib import Path
from click.testing import CliRunner
from labvault.cli.main import cli

runner = CliRunner()

def test_help():
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert "LabVault" in result.output

def test_init(tmp_path: Path):
    result = runner.invoke(cli, ['init', str(tmp_path / "testvault")])
    assert result.exit_code == 0
    assert "Vault initialized" in result.output
    assert (tmp_path / "testvault" / "labvault.db").exists()

def test_full_workflow(tmp_path: Path):
    """End-to-end: init -> project add -> experiment add -> run start -> run log -> show."""
    vault_path = str(tmp_path / "vault")

    # Init
    result = runner.invoke(cli, ['init', vault_path])
    assert result.exit_code == 0

    # Project add
    result = runner.invoke(cli, ['project', 'add', 'My Research', '--vault', vault_path])
    assert result.exit_code == 0
    assert "Created project" in result.output

    # Project ls
    result = runner.invoke(cli, ['project', 'ls', '--vault', vault_path])
    assert result.exit_code == 0
    assert "My Research" in result.output

    # Experiment add
    result = runner.invoke(cli, ['experiment', 'add', 'my-research', 'LR Sweep', '--vault', vault_path])
    assert result.exit_code == 0
    assert "Created experiment" in result.output

    # Experiment ls
    result = runner.invoke(cli, ['experiment', 'ls', 'my-research', '--vault', vault_path])
    assert result.exit_code == 0
    assert "LR Sweep" in result.output

    # Run start with metrics and tags
    result = runner.invoke(cli, [
        'run', 'start', 'my-research', 'lr-sweep',
        '-m', 'accuracy=0.92', '-t', 'env=local',
        '--notes', 'baseline run',
        '--vault', vault_path
    ])
    assert result.exit_code == 0
    assert "v1" in result.output

    # Run log additional metrics
    result = runner.invoke(cli, [
        'run', 'log', 'my-research', 'lr-sweep', '1',
        '-m', 'f1=0.88', '-t', 'gpu=A100',
        '--vault', vault_path
    ])
    assert result.exit_code == 0
    assert "Logged to" in result.output

    # Artifact add
    dummy = tmp_path / "weights.pt"
    dummy.write_text("fake model data")
    result = runner.invoke(cli, [
        'artifact', 'add', 'my-research', 'lr-sweep', '1',
        str(dummy),
        '--vault', vault_path
    ])
    assert result.exit_code == 0
    assert "Added artifact" in result.output

    # Show
    result = runner.invoke(cli, ['show', 'my-research', 'lr-sweep', '--vault', vault_path])
    assert result.exit_code == 0
    assert "v1" in result.output

def test_project_not_found(tmp_path: Path):
    vault_path = str(tmp_path / "vault")
    runner.invoke(cli, ['init', vault_path])
    result = runner.invoke(cli, ['experiment', 'add', 'nonexistent', 'Exp', '--vault', vault_path])
    assert result.exit_code == 1

def test_second_run_gets_v2(tmp_path: Path):
    vault_path = str(tmp_path / "vault")
    runner.invoke(cli, ['init', vault_path])
    runner.invoke(cli, ['project', 'add', 'P', '--vault', vault_path])
    runner.invoke(cli, ['experiment', 'add', 'p', 'E', '--vault', vault_path])
    runner.invoke(cli, ['run', 'start', 'p', 'e', '--vault', vault_path])
    result = runner.invoke(cli, ['run', 'start', 'p', 'e', '--vault', vault_path])
    assert result.exit_code == 0
    assert "v2" in result.output
