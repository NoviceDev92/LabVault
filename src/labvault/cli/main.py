import click

@click.group()
@click.version_option()
def cli():
    """LabVault - Local MLOps Experiment Vault."""
    pass

if __name__ == "__main__":
    cli()
