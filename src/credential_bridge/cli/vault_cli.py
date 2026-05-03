# src/credential_bridge/cli/vault_cli.py
from typing import List, Optional

import typer
from prompt_toolkit import prompt as pt_prompt
from prompt_toolkit.styles import Style as PtStyle

from ..backends.vault import VaultBackend
from ..exceptions import CredentialBridgeError, VaultSecretNotFoundError
from ._output import console, err_console, print_error, print_result, print_success, print_table

app = typer.Typer(name="vault", help="HashiCorp Vault secret operations", no_args_is_help=True)

_pt_style = PtStyle.from_dict({"prompt": "fg:ansibrightgreen bold"})

# Shared auth option defaults
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
        print_error(str(e), title="Configuration Error")
        raise typer.Exit(1)


def _prompt_secrets_interactive() -> List[str]:
    """Interactively prompt for KEY=value pairs when --secret is omitted."""
    secrets = []
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
    name: str = typer.Argument(..., help="Secret path (e.g. myapp/database)"),
    secret: Optional[List[str]] = typer.Option(None, "--secret", "-s", help="KEY=value pair (repeatable)"),
    vault_url: Optional[str] = _VAULT_URL,
    vault_token: Optional[str] = _VAULT_TOKEN,
    role_id: Optional[str] = _ROLE_ID,
    secret_id: Optional[str] = _SECRET_ID,
    service_name: str = _SERVICE_NAME,
    mount_point: str = _MOUNT_POINT,
):
    """Add a secret to Vault."""
    if not secret:
        secret = _prompt_secrets_interactive()
    if not secret:
        print_error("At least one KEY=value pair is required.", title="Missing Input")
        raise typer.Exit(1)
    backend = _make_backend(vault_url, vault_token, role_id, secret_id, service_name, mount_point)
    secret_dict = dict(s.split("=", 1) for s in secret)
    try:
        backend.add_secret(name, secret_dict)
        print_success(f"Secret [bold]{name}[/bold] added.")
    except CredentialBridgeError as e:
        print_error(str(e))
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
    output: str = typer.Option("rich", "--output", "-o", help="Output format: rich (default) or json"),
):
    """Retrieve a secret from Vault."""
    backend = _make_backend(vault_url, vault_token, role_id, secret_id, service_name, mount_point)
    try:
        result = backend.get_secret(name)
        if output == "json":
            import json as _json
            typer.echo(_json.dumps(result))
        else:
            print_result(result, title=name)
    except VaultSecretNotFoundError:
        print_error(f"Secret [bold]{name}[/bold] does not exist.", title="Not Found")
        raise typer.Exit(1)
    except CredentialBridgeError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command()
def update(
    name: str = typer.Argument(..., help="Secret path"),
    secret: Optional[List[str]] = typer.Option(None, "--secret", "-s", help="KEY=value pair (repeatable)"),
    vault_url: Optional[str] = _VAULT_URL,
    vault_token: Optional[str] = _VAULT_TOKEN,
    role_id: Optional[str] = _ROLE_ID,
    secret_id: Optional[str] = _SECRET_ID,
    service_name: str = _SERVICE_NAME,
    mount_point: str = _MOUNT_POINT,
):
    """Update an existing Vault secret."""
    if not secret:
        secret = _prompt_secrets_interactive()
    if not secret:
        print_error("At least one KEY=value pair is required.", title="Missing Input")
        raise typer.Exit(1)
    backend = _make_backend(vault_url, vault_token, role_id, secret_id, service_name, mount_point)
    secret_dict = dict(s.split("=", 1) for s in secret)
    try:
        backend.update_secret(name, secret_dict)
        print_success(f"Secret [bold]{name}[/bold] updated.")
    except VaultSecretNotFoundError:
        print_error(f"Secret [bold]{name}[/bold] does not exist.", title="Not Found")
        raise typer.Exit(1)
    except CredentialBridgeError as e:
        print_error(str(e))
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
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Permanently delete a Vault secret and all its versions."""
    if not confirm:
        typer.confirm(f"Delete secret '{name}' and ALL versions?", abort=True)
    backend = _make_backend(vault_url, vault_token, role_id, secret_id, service_name, mount_point)
    try:
        backend.delete_secret(name)
        print_success(f"Secret [bold]{name}[/bold] permanently deleted.")
    except VaultSecretNotFoundError:
        print_error(f"Secret [bold]{name}[/bold] does not exist.", title="Not Found")
        raise typer.Exit(1)
    except CredentialBridgeError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command(name="list")
def list_secrets(
    path: str = typer.Argument("", help="Path prefix (default: root of mount)"),
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
        print_table(keys, title=f"Secrets at '{path or '/'}'")
    except CredentialBridgeError as e:
        print_error(str(e))
        raise typer.Exit(1)


def main():
    app()
