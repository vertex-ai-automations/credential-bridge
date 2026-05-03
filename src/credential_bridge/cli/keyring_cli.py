# src/credential_bridge/cli/keyring_cli.py
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
import json

from ..backends.keyring import KeyringBackend
from ..exceptions import CredentialBridgeError

app = typer.Typer(name="keyring", help="System keyring secret operations", no_args_is_help=True)
console = Console()
err_console = Console(stderr=True)

# Shared service-name option — defined once, referenced by each command
_SERVICE = typer.Option("default", "--service-name", "-s", help="Keyring service name (default: 'default')")


@app.command()
def add(
    name: str = typer.Argument(..., help="Secret key name"),
    secret: Optional[List[str]] = typer.Option(None, "--secret", help="KEY=value pairs"),
    service_name: str = _SERVICE,
):
    """Add a secret to the system keyring."""
    if not secret:
        typer.echo("Error: --secret is required", err=True)
        raise typer.Exit(1)
    backend = KeyringBackend(service_name=service_name)
    secret_dict = dict(s.split("=", 1) for s in secret)
    try:
        backend.add_secret(name, secret_dict)
        console.print(Panel(f"[green]✓[/green] Secret [bold]{name}[/bold] added.", title="Success"))
    except CredentialBridgeError as e:
        err_console.print(Panel(f"[red]{e}[/red]", title="Error"))
        raise typer.Exit(1)


@app.command()
def get(
    name: str = typer.Argument(..., help="Secret key name"),
    service_name: str = _SERVICE,
):
    """Retrieve a secret from the system keyring."""
    backend = KeyringBackend(service_name=service_name)
    try:
        result = backend.get_secret(name)
        syntax = Syntax(json.dumps(result, indent=2), "json", theme="monokai")
        console.print(Panel(syntax, title=f"[bold]{name}[/bold]"))
    except CredentialBridgeError as e:
        err_console.print(Panel(f"[red]{e}[/red]", title="Error"))
        raise typer.Exit(1)


@app.command()
def update(
    name: str = typer.Argument(..., help="Secret key name"),
    secret: Optional[List[str]] = typer.Option(None, "--secret", help="KEY=value pairs"),
    service_name: str = _SERVICE,
):
    """Update an existing keyring secret."""
    if not secret:
        typer.echo("Error: --secret is required", err=True)
        raise typer.Exit(1)
    backend = KeyringBackend(service_name=service_name)
    secret_dict = dict(s.split("=", 1) for s in secret)
    try:
        backend.update_secret(name, secret_dict)
        console.print(Panel(f"[green]✓[/green] Secret [bold]{name}[/bold] updated.", title="Success"))
    except CredentialBridgeError as e:
        err_console.print(Panel(f"[red]{e}[/red]", title="Error"))
        raise typer.Exit(1)


@app.command()
def delete(
    name: str = typer.Argument(..., help="Secret key name"),
    service_name: str = _SERVICE,
    confirm: bool = typer.Option(False, "--yes", "-y"),
):
    """Delete a secret from the system keyring."""
    if not confirm:
        typer.confirm(f"Delete secret '{name}'?", abort=True)
    backend = KeyringBackend(service_name=service_name)
    try:
        backend.delete_secret(name)
        console.print(Panel(f"[green]✓[/green] Secret [bold]{name}[/bold] deleted.", title="Success"))
    except CredentialBridgeError as e:
        err_console.print(Panel(f"[red]{e}[/red]", title="Error"))
        raise typer.Exit(1)


def main():
    app()
