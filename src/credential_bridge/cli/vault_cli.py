# src/credential_bridge/cli/vault_cli.py
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
import json

from ..backends.vault import VaultBackend
from ..exceptions import CredentialBridgeError

app = typer.Typer(name="vault", help="HashiCorp Vault secret operations", no_args_is_help=True)
console = Console()
err_console = Console(stderr=True)

# Shared auth option defaults — defined once, referenced by each command
_VAULT_URL    = typer.Option(None,              "--vault-url",       envvar="VAULT_ADDR",      help="Vault server URL (or set VAULT_ADDR)")
_VAULT_TOKEN  = typer.Option(None,              "--vault-token",     envvar="VAULT_TOKEN",     help="Vault token")
_ROLE_ID      = typer.Option(None,              "--vault-role-id",   envvar="VAULT_ROLE_ID",   help="AppRole role ID")
_SECRET_ID    = typer.Option(None,              "--vault-secret-id", envvar="VAULT_SECRET_ID", help="AppRole secret ID")
_SERVICE_NAME = typer.Option("default_service", "--service-name",                              help="Service name (logging tag)")
_MOUNT_POINT  = typer.Option("secret",          "--mount-point",                               help="Vault KV-v2 mount point")


def _make_backend(vault_url, vault_token, role_id, secret_id, service_name, mount_point):
    try:
        return VaultBackend(
            vault_url=vault_url,
            vault_token=vault_token,
            vault_role_id=role_id,
            vault_secret_id=secret_id,
            service_name=service_name,
            mount_point=mount_point,
        )
    except CredentialBridgeError as e:
        err_console.print(Panel(f"[red]{e}[/red]", title="Configuration Error"))
        raise typer.Exit(1)


@app.command()
def add(
    name: str = typer.Argument(..., help="Secret path"),
    secret: Optional[List[str]] = typer.Option(None, "--secret", help="KEY=value pairs"),
    vault_url: Optional[str] = _VAULT_URL,
    vault_token: Optional[str] = _VAULT_TOKEN,
    role_id: Optional[str] = _ROLE_ID,
    secret_id: Optional[str] = _SECRET_ID,
    service_name: str = _SERVICE_NAME,
    mount_point: str = _MOUNT_POINT,
):
    """Add a secret to Vault."""
    if not secret:
        typer.echo("Error: --secret is required (KEY=value)", err=True)
        raise typer.Exit(1)
    backend = _make_backend(vault_url, vault_token, role_id, secret_id, service_name, mount_point)
    secret_dict = dict(s.split("=", 1) for s in secret)
    try:
        backend.add_secret(name, secret_dict)
        console.print(Panel(f"[green]✓[/green] Secret [bold]{name}[/bold] added.", title="Success"))
    except CredentialBridgeError as e:
        err_console.print(Panel(f"[red]{e}[/red]", title="Error"))
        raise typer.Exit(1)


@app.command()
def get(
    name: str = typer.Argument(..., help="Secret path"),
    vault_url: Optional[str] = _VAULT_URL,
    vault_token: Optional[str] = _VAULT_TOKEN,
    role_id: Optional[str] = _ROLE_ID,
    secret_id: Optional[str] = _SECRET_ID,
    service_name: str = _SERVICE_NAME,
    mount_point: str = _MOUNT_POINT,
):
    """Retrieve a secret from Vault."""
    backend = _make_backend(vault_url, vault_token, role_id, secret_id, service_name, mount_point)
    try:
        result = backend.get_secret(name)
        syntax = Syntax(json.dumps(result, indent=2), "json", theme="monokai")
        console.print(Panel(syntax, title=f"[bold]{name}[/bold]"))
    except CredentialBridgeError as e:
        err_console.print(Panel(f"[red]{e}[/red]", title="Error"))
        raise typer.Exit(1)


@app.command()
def update(
    name: str = typer.Argument(..., help="Secret path"),
    secret: Optional[List[str]] = typer.Option(None, "--secret", help="KEY=value pairs"),
    vault_url: Optional[str] = _VAULT_URL,
    vault_token: Optional[str] = _VAULT_TOKEN,
    role_id: Optional[str] = _ROLE_ID,
    secret_id: Optional[str] = _SECRET_ID,
    service_name: str = _SERVICE_NAME,
    mount_point: str = _MOUNT_POINT,
):
    """Update an existing Vault secret."""
    if not secret:
        typer.echo("Error: --secret is required", err=True)
        raise typer.Exit(1)
    backend = _make_backend(vault_url, vault_token, role_id, secret_id, service_name, mount_point)
    secret_dict = dict(s.split("=", 1) for s in secret)
    try:
        backend.update_secret(name, secret_dict)
        console.print(Panel(f"[green]✓[/green] Secret [bold]{name}[/bold] updated.", title="Success"))
    except CredentialBridgeError as e:
        err_console.print(Panel(f"[red]{e}[/red]", title="Error"))
        raise typer.Exit(1)


@app.command()
def delete(
    name: str = typer.Argument(..., help="Secret path"),
    vault_url: Optional[str] = _VAULT_URL,
    vault_token: Optional[str] = _VAULT_TOKEN,
    role_id: Optional[str] = _ROLE_ID,
    secret_id: Optional[str] = _SECRET_ID,
    service_name: str = _SERVICE_NAME,
    mount_point: str = _MOUNT_POINT,
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Permanently delete a Vault secret."""
    if not confirm:
        typer.confirm(f"Delete secret '{name}' and ALL versions?", abort=True)
    backend = _make_backend(vault_url, vault_token, role_id, secret_id, service_name, mount_point)
    try:
        backend.delete_secret(name)
        console.print(Panel(f"[green]✓[/green] Secret [bold]{name}[/bold] deleted.", title="Success"))
    except CredentialBridgeError as e:
        err_console.print(Panel(f"[red]{e}[/red]", title="Error"))
        raise typer.Exit(1)


@app.command(name="list")
def list_secrets(
    path: str = typer.Argument("", help="Path prefix"),
    vault_url: Optional[str] = _VAULT_URL,
    vault_token: Optional[str] = _VAULT_TOKEN,
    role_id: Optional[str] = _ROLE_ID,
    secret_id: Optional[str] = _SECRET_ID,
    service_name: str = _SERVICE_NAME,
    mount_point: str = _MOUNT_POINT,
):
    """List secrets at a Vault path."""
    backend = _make_backend(vault_url, vault_token, role_id, secret_id, service_name, mount_point)
    try:
        keys = backend.list_secrets(path)
        table = Table(title=f"Secrets at '{path or '/'}'")
        table.add_column("Key", style="cyan")
        for k in keys:
            table.add_row(k)
        console.print(table)
    except CredentialBridgeError as e:
        err_console.print(Panel(f"[red]{e}[/red]", title="Error"))
        raise typer.Exit(1)


def main():
    app()
