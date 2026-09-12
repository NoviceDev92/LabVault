from click.testing import CliRunner
from labvault.cli.main import cli

def test_help():
    runner = CliRunner()
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert "LabVault" in result.output
