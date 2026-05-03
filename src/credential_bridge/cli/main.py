# src/credential_bridge/cli/main.py
import typer
from importlib.metadata import version, PackageNotFoundError

from .env_cli import app as env_app
from .keyring_cli import app as keyring_app
from .vault_cli import app as vault_app

app = typer.Typer(
    name="cb",
    help="Credential Bridge — unified secrets management CLI",
    no_args_is_help=True,
)

app.add_typer(vault_app, name="vault")
app.add_typer(keyring_app, name="keyring")
app.add_typer(env_app, name="env")


def _version_callback(value: bool) -> None:
    if value:
        try:
            ver = version("credential-bridge")
        except PackageNotFoundError:
            ver = "unknown"
        typer.echo(f"cb version {ver}")
        raise typer.Exit()


@app.callback()
def root_callback(
    version: bool = typer.Option(  # noqa: F811
        False, "--version", "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """Credential Bridge — unified secrets management CLI."""


@app.command()
def wizard():
    """Launch the interactive secrets wizard."""
    from ..prompt_wizard import main as _wizard_main
    _wizard_main()


def main():
    """Entry point registered in pyproject.toml as cb = credential_bridge.cli.main:main"""
    app()
