# src/credential_bridge/prompt_wizard.py
import sys
from typing import Optional

# Ensure Rich can render Unicode (box lines, checkmarks) on Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except AttributeError:
        pass

from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from .utils import get_vault_credentials, load_config, load_welcome_banner, save_config

# ── Rich console ──────────────────────────────────────────────────────────────
console = Console()

# ── prompt_toolkit styles ─────────────────────────────────────────────────────
_opt_style = Style.from_dict({"prompt": "fg:ansibrightcyan bold"})
_entry_style = Style.from_dict({"prompt": "fg:ansibrightgreen bold"})

# ── Shared history (persists across all prompts in a session) ─────────────────
_history = InMemoryHistory()


# ── Output helpers ─────────────────────────────────────────────────────────────

def _success(msg: str) -> None:
    console.print(f"  [green]✓[/green]  {msg}")


def _error(msg: str) -> None:
    console.print(f"  [red]✗[/red]  [red]{msg}[/red]")


def _info(msg: str) -> None:
    console.print(f"  [cyan]ℹ[/cyan]  [dim]{msg}[/dim]")


def _section(title: str) -> None:
    console.print(Rule(f"[bold #7c3aed]{title}[/bold #7c3aed]", style="#3730a3"))
    console.print()


def _print_banner() -> None:
    """Render the ASCII welcome banner with Rich styling."""
    try:
        ascii_art = load_welcome_banner("welcome_banner.txt")
    except Exception:
        ascii_art = "Credential Bridge"

    # Render banner on a wide console so the ASCII art never wraps
    from rich.console import Console as _Console
    wide = _Console(width=120)

    art = Text(ascii_art, style="bold #7c3aed", no_wrap=True, justify="center")
    tagline = Text(
        "\nUnified secrets management  ·  Vault  ·  Keyring  ·  .env",
        style="dim #a78bfa",
        justify="center",
    )
    combined = Text.assemble(art, tagline)

    wide.print(
        Panel(
            Align.center(combined),
            border_style="#3730a3",
            padding=(1, 4),
        )
    )
    wide.print()


def _print_result_dict(data: dict, title: str = "") -> None:
    """Display a secret dict as a syntax-highlighted JSON panel."""
    import json
    syntax = Syntax(json.dumps(data, indent=2), "json", theme="monokai")
    console.print(
        Panel(
            syntax,
            title=f"[bold cyan]{title}[/bold cyan]" if title else "",
            border_style="cyan",
            padding=(0, 1),
        )
    )


def _print_result_list(keys: list, title: str = "") -> None:
    """Display a list of keys as a Rich table."""
    min_width = len(title) + 4 if title else 20
    table = Table(title=title, border_style="cyan", show_header=True,
                  header_style="bold cyan", min_width=min_width)
    table.add_column("Key", style="cyan")
    for k in keys:
        table.add_row(str(k))
    console.print(table)


def _prompt(text: str, completer=None, is_password: bool = False) -> str:
    """Wrapper around prompt_toolkit's prompt with shared history."""
    return prompt(
        HTML(text),
        completer=completer,
        history=_history,
        style=_entry_style,
        is_password=is_password,
    ).strip()


def _menu_prompt(text: str, completer=None) -> str:
    """Menu-style prompt with cyan styling."""
    return prompt(
        HTML(text),
        completer=completer,
        history=_history,
        style=_opt_style,
    ).strip().lower()


# ── Vault credential validation ───────────────────────────────────────────────

def is_vault_cred_valid(vault_token=None, role_id=None, secret_id=None) -> bool:
    """Validate Vault credentials by attempting authentication through VaultBackend."""
    import os
    vault_addr = os.environ.get("VAULT_ADDR", "")
    if not vault_addr:
        _error("VAULT_ADDR environment variable is not set.")
        return False
    try:
        from .manager import SecretsManager
        kwargs: dict = {"vault_url": vault_addr}
        if vault_token:
            kwargs["vault_token"] = vault_token
        elif role_id and secret_id:
            kwargs["vault_role_id"] = role_id
            kwargs["vault_secret_id"] = secret_id
        else:
            _error("No credentials provided.")
            return False
        SecretsManager("vault", **kwargs)
        return True
    except Exception as e:
        _error(f"Authentication failed: {e}")
        return False


# ── Main entry point ─────────────────────────────────────────────────────────

def main() -> None:
    _print_banner()
    while True:
        _section("Main Menu")
        service_completer = WordCompleter(
            ["keyring", "vault", "env", "exit"], ignore_case=True
        )
        try:
            service = _menu_prompt(
                "<b><ansibrightcyan>▶ Backend</ansibrightcyan></b>"
                "  <ansiwhite>(keyring / vault / env / exit):</ansiwhite>  ",
                completer=service_completer,
            )
        except (KeyboardInterrupt, EOFError):
            _goodbye()
            sys.exit(0)

        if service == "keyring":
            configure_keyring()
        elif service == "vault":
            configure_vault()
        elif service == "env":
            configure_env()
        elif service == "exit":
            _goodbye()
            sys.exit(0)
        else:
            _error(f"Unknown selection '{service}'. Choose: keyring, vault, env, or exit.")


def _goodbye() -> None:
    console.print()
    console.print(
        Panel(
            "[bold #7c3aed]Thank you for using Credential Bridge. Goodbye! 👋[/bold #7c3aed]",
            border_style="#3730a3",
            padding=(0, 2),
        )
    )


# ── Keyring menu ─────────────────────────────────────────────────────────────

def configure_keyring() -> None:
    while True:
        _section("Keyring")
        action_completer = WordCompleter(
            ["add", "update", "delete", "get", "back"], ignore_case=True
        )
        action = _menu_prompt(
            "<b><ansibrightcyan>[Keyring]</ansibrightcyan></b>"
            "  <ansiwhite>(add / get / update / delete / back):</ansiwhite>  ",
            completer=action_completer,
        )

        if action == "back":
            return
        if action not in ["add", "update", "delete", "get"]:
            _error(f"Unknown action '{action}'.")
            continue

        service_name = _prompt("<b><ansibrightgreen>  Service name:</ansibrightgreen></b>  ")
        name = _prompt("<b><ansibrightgreen>  Secret name:</ansibrightgreen></b>   ")
        secret: Optional[str] = None

        if action in ["add", "update"]:
            secret = _prompt(
                "<b><ansibrightgreen>  Secret value:</ansibrightgreen></b>  ",
                is_password=True,
            )

        run_keyring_cli(action, service_name, name, secret)
        console.print()


# ── Vault menu ────────────────────────────────────────────────────────────────

def configure_vault() -> None:
    while True:
        _section("Vault  ·  Authentication")
        auth_completer = WordCompleter(
            ["vault_token", "approle", "back"], ignore_case=True
        )
        auth_type = _menu_prompt(
            "<b><ansibrightcyan>[Vault]</ansibrightcyan></b>"
            "  <ansiwhite>(vault_token / approle / back):</ansiwhite>  ",
            completer=auth_completer,
        )

        if auth_type == "back":
            return
        if auth_type not in ["vault_token", "approle"]:
            _error(f"Unknown auth type '{auth_type}'.")
            continue

        vault_token, vault_role_id, vault_secret_id = get_vault_credentials()

        if auth_type == "vault_token":
            if not vault_token:
                vault_token = _prompt(
                    "<b><ansibrightgreen>  Vault Token:</ansibrightgreen></b>  ",
                    is_password=True,
                )
                if is_vault_cred_valid(vault_token=vault_token):
                    _save_vault_token(vault_token)
                    _success("Vault token saved.")
                else:
                    _error("Invalid token. Please try again.")
                    continue
            else:
                if not is_vault_cred_valid(vault_token=vault_token):
                    _info("Existing Vault token has expired or is invalid. Please enter a new one.")
                    vault_token = _prompt(
                        "<b><ansibrightgreen>  New Vault Token:</ansibrightgreen></b>  ",
                        is_password=True,
                    )
                    if is_vault_cred_valid(vault_token=vault_token):
                        _save_vault_token(vault_token)
                        _success("Vault token updated.")
                    else:
                        _error("Invalid token. Please try again.")
                        continue
                else:
                    _success("Existing token is valid.")

        elif auth_type == "approle":
            if not (vault_role_id and vault_secret_id):
                vault_role_id = _prompt(
                    "<b><ansibrightgreen>  Role ID:</ansibrightgreen></b>    ",
                    is_password=True,
                )
                vault_secret_id = _prompt(
                    "<b><ansibrightgreen>  Secret ID:</ansibrightgreen></b>  ",
                    is_password=True,
                )
                if is_vault_cred_valid(role_id=vault_role_id, secret_id=vault_secret_id):
                    _save_vault_approle(vault_role_id, vault_secret_id)
                    _success("AppRole credentials saved.")
                else:
                    _error("Invalid AppRole credentials. Please try again.")
                    continue
            else:
                if not is_vault_cred_valid(role_id=vault_role_id, secret_id=vault_secret_id):
                    _info("Existing AppRole credentials have expired or are invalid. Please enter new ones.")
                    vault_role_id = _prompt(
                        "<b><ansibrightgreen>  New Role ID:</ansibrightgreen></b>    ",
                        is_password=True,
                    )
                    vault_secret_id = _prompt(
                        "<b><ansibrightgreen>  New Secret ID:</ansibrightgreen></b>  ",
                        is_password=True,
                    )
                    if is_vault_cred_valid(role_id=vault_role_id, secret_id=vault_secret_id):
                        _save_vault_approle(vault_role_id, vault_secret_id)
                        _success("AppRole credentials updated.")
                    else:
                        _error("Invalid credentials. Please try again.")
                        continue
                else:
                    _success("Existing AppRole credentials are valid.")

        _vault_action_loop(auth_type, vault_token=vault_token, vault_role_id=vault_role_id, vault_secret_id=vault_secret_id)
        return


def _save_vault_token(token: str) -> None:
    import os
    cfg = load_config()
    cfg.update({
        "vault_token": token,
        "vault_role_id": None,
        "vault_secret_id": None,
        "vault_addr": os.environ.get("VAULT_ADDR", ""),
    })
    save_config(cfg)


def _save_vault_approle(role_id: str, secret_id: str) -> None:
    import os
    cfg = load_config()
    cfg.update({
        "vault_role_id": role_id,
        "vault_secret_id": secret_id,
        "vault_token": None,
        "vault_addr": os.environ.get("VAULT_ADDR", ""),
    })
    save_config(cfg)


def _vault_action_loop(auth_label: str, vault_token=None, vault_role_id=None, vault_secret_id=None) -> None:
    _VAULT_ACTIONS = [
        "add", "update", "delete", "get", "list",
        "read-metadata", "delete-versions", "undelete-versions",
        "destroy-versions", "get-config", "back",
    ]
    action_completer = WordCompleter(_VAULT_ACTIONS, ignore_case=True)

    while True:
        _section(f"Vault  ·  {auth_label.replace('_', ' ').title()}")
        action = _menu_prompt(
            f"<b><ansibrightcyan>[Vault › {auth_label}]</ansibrightcyan></b>"
            "  <ansiwhite>(add/get/update/delete/list/… /back):</ansiwhite>  ",
            completer=action_completer,
        )

        if action == "back":
            return
        if action not in _VAULT_ACTIONS:
            _error(f"Unknown action '{action}'.")
            continue

        service_name = _prompt(
            "<b><ansibrightgreen>  Service name (tag):</ansibrightgreen></b>    "
        )
        secret_path = _prompt(
            "<b><ansibrightgreen>  Secret path (e.g. myapp/db):</ansibrightgreen></b>  "
        )

        secret_data: dict = {}
        versions = None

        if action in ["add", "update"]:
            while True:
                try:
                    num = int(
                        _prompt(
                            "<b><ansibrightgreen>  Number of key-value pairs:</ansibrightgreen></b>  "
                        )
                    )
                    break
                except ValueError:
                    _error("Please enter a numeric value.")

            for i in range(num):
                k = _prompt(f"<b><ansibrightgreen>  Key {i + 1}:</ansibrightgreen></b>    ")
                v = _prompt(
                    f"<b><ansibrightgreen>  Value {i + 1}:</ansibrightgreen></b>  ",
                    is_password=True,
                )
                secret_data[k] = v

        if action in ["delete-versions", "undelete-versions", "destroy-versions"]:
            while True:
                try:
                    num = int(
                        _prompt(
                            "<b><ansibrightgreen>  Number of versions:</ansibrightgreen></b>  "
                        )
                    )
                    versions = []
                    for _ in range(num):
                        versions.append(
                            int(_prompt("<b><ansibrightgreen>  Version number:</ansibrightgreen></b>  "))
                        )
                    break
                except ValueError:
                    _error("Please enter numeric values for versions.")

        run_vault_cli(action, service_name, secret_path, secret_data, versions,
                      vault_token=vault_token, vault_role_id=vault_role_id, vault_secret_id=vault_secret_id)
        console.print()


# ── .env menu ────────────────────────────────────────────────────────────────

def configure_env() -> None:
    _section(".env File")
    env_path = _prompt(
        "<b><ansibrightgreen>  .env file path</ansibrightgreen></b>"
        "  <ansiwhite>(default: .env):</ansiwhite>  "
    ) or ".env"

    from .backends.env_file import EnvFileBackend

    while True:
        _section(f".env  ·  {env_path}")
        action_completer = WordCompleter(
            ["add", "get", "update", "delete", "list", "back"], ignore_case=True
        )
        action = _menu_prompt(
            f"<b><ansibrightcyan>[.env › {env_path}]</ansibrightcyan></b>"
            "  <ansiwhite>(add / get / update / delete / list / back):</ansiwhite>  ",
            completer=action_completer,
        )

        if action == "back":
            return
        if action not in ["add", "get", "update", "delete", "list"]:
            _error(f"Unknown action '{action}'.")
            continue

        backend = EnvFileBackend(path=env_path)

        try:
            if action == "list":
                keys = backend.list_secrets()
                _print_result_list(keys, title=f"Keys in {env_path}")

            elif action in ["add", "update"]:
                name = _prompt("<b><ansibrightgreen>  Key name:</ansibrightgreen></b>   ")
                value = _prompt("<b><ansibrightgreen>  Value:</ansibrightgreen></b>      ")
                if action == "add":
                    backend.add_secret(name, {name: value})
                else:
                    backend.update_secret(name, {name: value})
                _success(f"{action.capitalize()} successful: [bold]{name}[/bold]")

            elif action == "get":
                name = _prompt("<b><ansibrightgreen>  Key name:</ansibrightgreen></b>  ")
                result = backend.get_secret(name)
                _print_result_dict(result, title=name)

            elif action == "delete":
                name = _prompt("<b><ansibrightgreen>  Key name:</ansibrightgreen></b>  ")
                backend.delete_secret(name)
                _success(f"Deleted [bold]{name}[/bold] from {env_path}.")

        except Exception as e:
            _error(str(e))

        console.print()


# ── Dispatch helpers ─────────────────────────────────────────────────────────

def run_keyring_cli(action: str, service_name: str, name: str, secret: Optional[str]) -> None:
    from .manager import SecretsManager
    manager = SecretsManager("keyring", service_name=service_name)
    try:
        if action == "add":
            manager.add_secret(name, {name: secret})
            _success(f"Added [bold]{name}[/bold] to keyring service '{service_name}'.")
        elif action == "get":
            result = manager.get_secret(name)
            _print_result_dict(result, title=name)
        elif action == "update":
            manager.update_secret(name, {name: secret})
            _success(f"Updated [bold]{name}[/bold] in keyring service '{service_name}'.")
        elif action == "delete":
            manager.delete_secret(name)
            _success(f"Deleted [bold]{name}[/bold] from keyring service '{service_name}'.")
    except Exception as e:
        _error(str(e))


def run_vault_cli(
    action: str,
    service_name: str,
    secret_path: str,
    secret_data: dict,
    versions=None,
    vault_token=None,
    vault_role_id=None,
    vault_secret_id=None,
) -> None:
    import os
    from .manager import SecretsManager
    vault_url = os.environ.get("VAULT_ADDR") or load_config().get("vault_addr")
    manager = SecretsManager(
        "vault",
        service_name=service_name,
        vault_url=vault_url,
        vault_token=vault_token,
        vault_role_id=vault_role_id,
        vault_secret_id=vault_secret_id,
    )
    try:
        if action == "add":
            manager.add_secret(secret_path, secret_data)
            _success(f"Secret [bold]{secret_path}[/bold] added.")
        elif action == "get":
            result = manager.get_secret(secret_path)
            _print_result_dict(result, title=secret_path)
        elif action == "update":
            manager.update_secret(secret_path, secret_data)
            _success(f"Secret [bold]{secret_path}[/bold] updated.")
        elif action == "delete":
            manager.delete_secret(secret_path)
            _success(f"Secret [bold]{secret_path}[/bold] deleted.")
        elif action == "list":
            keys = manager.list_secrets(secret_path)
            _print_result_list(keys, title=f"Secrets at {secret_path or '/'}")
        elif action in ("read-metadata", "delete-versions", "undelete-versions",
                        "destroy-versions", "get-config"):
            vault_backend = manager.backend
            if action == "read-metadata":
                meta = vault_backend.read_secret_metadata(secret_path)
                _print_result_dict(meta, title=f"Metadata: {secret_path}")
            elif action == "delete-versions":
                vault_backend.delete_secret_versions(secret_path, versions)
                _success(f"Soft-deleted versions {versions} of [bold]{secret_path}[/bold].")
            elif action == "undelete-versions":
                vault_backend.undelete_secret_versions(secret_path, versions)
                _success(f"Restored versions {versions} of [bold]{secret_path}[/bold].")
            elif action == "destroy-versions":
                vault_backend.destroy_secret_versions(secret_path, versions)
                _success(f"Permanently destroyed versions {versions} of [bold]{secret_path}[/bold].")
            elif action == "get-config":
                cfg = vault_backend.get_config()
                _print_result_dict(cfg, title="Vault Config")
    except Exception as e:
        _error(str(e))


if __name__ == "__main__":
    main()
