# src/credential_bridge/cli/keyring_cli.py
from typing import List, Optional

import typer
from prompt_toolkit import prompt as pt_prompt
from prompt_toolkit.styles import Style as PtStyle

from ..backends.keyring import KeyringBackend
from ..exceptions import CredentialBridgeError
from ._output import print_error, print_result, print_success

app = typer.Typer(name="keyring", help="System keyring secret operations", no_args_is_help=True)

_pt_style = PtStyle.from_dict({"prompt": "fg:ansibrightgreen bold"})
_SERVICE = typer.Option("default", "--service-name", "-s", help="Keyring service name (default: 'default')")


def _prompt_secrets_interactive() -> List[str]:
    secrets = []
    from ._output import console
    console.print("[dim]Enter secrets interactively. Leave KEY blank to finish.[/dim]")
    while True:
        key = pt_prompt("  Key   : ", style=_pt_style).strip()
        if not key:
            break
        value = pt_prompt("  Value : ", style=_pt_style, is_password=True).strip()
        secrets.append(f"{key}={value}")
    return secrets


@app.command()
def add(
    name: str = typer.Argument(..., help="Secret key name"),
    secret: Optional[List[str]] = typer.Option(None, "--secret", help="KEY=value pair (repeatable)"),
    service_name: str = _SERVICE,
):
    """Add a secret to the system keyring."""
    if not secret:
        secret = _prompt_secrets_interactive()
    if not secret:
        print_error("At least one KEY=value pair is required.", title="Missing Input")
        raise typer.Exit(1)
    backend = KeyringBackend(service_name=service_name)
    secret_dict = dict(s.split("=", 1) for s in secret)
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
            import json as _json
            typer.echo(_json.dumps(result))
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
        secret = _prompt_secrets_interactive()
    if not secret:
        print_error("At least one KEY=value pair is required.", title="Missing Input")
        raise typer.Exit(1)
    backend = KeyringBackend(service_name=service_name)
    secret_dict = dict(s.split("=", 1) for s in secret)
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
