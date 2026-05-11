# src/credential_bridge/cli/env_cli.py
import json
from typing import List, Optional

import typer

from ..backends.env_file import EnvFileBackend
from ..exceptions import CredentialBridgeError
from ._output import parse_secrets, prompt_secrets_interactive, print_error, print_result, print_success, print_table

app = typer.Typer(name="env", help=".env file secret operations", no_args_is_help=True)

_PATH = typer.Option(".env", "--path", "-p", help="Path to the .env file (default: .env in CWD)")


@app.command()
def add(
    name: str = typer.Argument(..., help="Group label / key name"),
    secret: Optional[List[str]] = typer.Option(None, "--secret", "-s", help="KEY=value pair (repeatable)"),
    path: str = _PATH,
):
    """Add a secret to the .env file."""
    if not secret:
        secret = prompt_secrets_interactive(mask_value=False)
    if not secret:
        print_error("At least one KEY=value pair is required.", title="Missing Input")
        raise typer.Exit(1)
    backend = EnvFileBackend(path=path)
    secret_dict = parse_secrets(secret)
    try:
        backend.add_secret(name, secret_dict)
        print_success(f"Secret [bold]{name}[/bold] added to [dim]{path}[/dim].")
    except CredentialBridgeError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command()
def get(
    name: str = typer.Argument(..., help="Env var key name"),
    path: str = _PATH,
    output: str = typer.Option("rich", "--output", "-o", help="Output format: rich or json"),
):
    """Get a secret from the .env file."""
    backend = EnvFileBackend(path=path)
    try:
        result = backend.get_secret(name)
        if output == "json":
            typer.echo(json.dumps(result))
        else:
            print_result(result, title=name)
    except CredentialBridgeError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command()
def update(
    name: str = typer.Argument(..., help="Env var key name"),
    secret: Optional[List[str]] = typer.Option(None, "--secret", "-s", help="KEY=value pair (repeatable)"),
    path: str = _PATH,
):
    """Update a secret in the .env file."""
    if not secret:
        secret = prompt_secrets_interactive(mask_value=False)
    if not secret:
        print_error("At least one KEY=value pair is required.", title="Missing Input")
        raise typer.Exit(1)
    backend = EnvFileBackend(path=path)
    secret_dict = parse_secrets(secret)
    try:
        backend.update_secret(name, secret_dict)
        print_success(f"[bold]{name}[/bold] updated in [dim]{path}[/dim].")
    except CredentialBridgeError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command()
def delete(
    name: str = typer.Argument(..., help="Env var key name"),
    path: str = _PATH,
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Delete a secret from the .env file."""
    if not confirm:
        typer.confirm(f"Delete '{name}' from {path}?", abort=True)
    backend = EnvFileBackend(path=path)
    try:
        backend.delete_secret(name)
        print_success(f"[bold]{name}[/bold] deleted from [dim]{path}[/dim].")
    except CredentialBridgeError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command(name="list")
def list_secrets(
    path: str = _PATH,
    output: str = typer.Option("rich", "--output", "-o", help="Output format: rich or json"),
):
    """List all keys in the .env file."""
    backend = EnvFileBackend(path=path)
    try:
        keys = backend.list_secrets()
        if output == "json":
            typer.echo(json.dumps(keys))
        else:
            print_table(keys, title=f"Keys in {path}")
    except CredentialBridgeError as e:
        print_error(str(e))
        raise typer.Exit(1)


def main():
    app()


if __name__ == "__main__":
    main()
