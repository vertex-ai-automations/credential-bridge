# src/credential_bridge/cli/keyring_cli.py
import json
from typing import List, Optional

import typer

from ..backends.keyring import KeyringBackend
from ..exceptions import CredentialBridgeError
from ._output import parse_secrets, prompt_secrets_interactive, print_error, print_result, print_success

app = typer.Typer(name="keyring", help="System keyring secret operations", no_args_is_help=True)

_SERVICE = typer.Option("default", "--service-name", "-s", help="Keyring service name (default: 'default')")


@app.command()
def add(
    name: str = typer.Argument(..., help="Secret key name"),
    secret: Optional[List[str]] = typer.Option(None, "--secret", help="KEY=value pair (repeatable)"),
    service_name: str = _SERVICE,
):
    """Add a secret to the system keyring."""
    if not secret:
        secret = prompt_secrets_interactive()
    if not secret:
        print_error("At least one KEY=value pair is required.", title="Missing Input")
        raise typer.Exit(1)
    backend = KeyringBackend(service_name=service_name)
    secret_dict = parse_secrets(secret)
    try:
        backend.add_secret(name, secret_dict)
        print_success(f"Secret [bold]{name}[/bold] added.")
    except CredentialBridgeError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command()
def get(
    name: str = typer.Argument(..., help="Secret key name"),
    service_name: str = _SERVICE,
    output: str = typer.Option("rich", "--output", "-o", help="Output format: rich or json"),
):
    """Retrieve a secret from the system keyring."""
    backend = KeyringBackend(service_name=service_name)
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
    name: str = typer.Argument(..., help="Secret key name"),
    secret: Optional[List[str]] = typer.Option(None, "--secret", help="KEY=value pair (repeatable)"),
    service_name: str = _SERVICE,
):
    """Update an existing keyring secret."""
    if not secret:
        secret = prompt_secrets_interactive()
    if not secret:
        print_error("At least one KEY=value pair is required.", title="Missing Input")
        raise typer.Exit(1)
    backend = KeyringBackend(service_name=service_name)
    secret_dict = parse_secrets(secret)
    try:
        backend.update_secret(name, secret_dict)
        print_success(f"Secret [bold]{name}[/bold] updated.")
    except CredentialBridgeError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command()
def delete(
    name: str = typer.Argument(..., help="Secret key name"),
    service_name: str = _SERVICE,
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Delete a secret from the system keyring."""
    if not confirm:
        typer.confirm(f"Delete secret '{name}'?", abort=True)
    backend = KeyringBackend(service_name=service_name)
    try:
        backend.delete_secret(name)
        print_success(f"Secret [bold]{name}[/bold] deleted.")
    except CredentialBridgeError as e:
        print_error(str(e))
        raise typer.Exit(1)


def main():
    app()


if __name__ == "__main__":
    main()
