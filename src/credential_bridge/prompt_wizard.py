# import subprocess
import sys

import hvac
from prompt_toolkit import print_formatted_text, prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style

from .cli.keyring_cli import handle_commands as keyring_handle
from .cli.vault_cli import handle_commands as vault_handle
from .keyring_manager import KeyringManager
from .utils import get_session, get_vault_credentials, load_welcome_banner, load_config, save_config
from .vault_manager import VaultManager

welcome_banner = load_welcome_banner("welcome_banner.txt")

style_banner = f"<b><yellow>{welcome_banner}</yellow></b>"

option_style = Style.from_dict({"prompt": "fg:ansibrightcyan bold"})
entry_style = Style.from_dict({"prompt": "fg:ansibrightgreen bold"})


def is_vault_cred_valid(vault_addr=None, vault_token=None, role_id=None, secret_id=None):
    """Check if the provided vault token is valid."""
    if not vault_addr:
        print("❌ Vault address is required.")
        return False
    if vault_token:
        try:
            client = hvac.Client(url=vault_addr, token=vault_token, session=get_session(), verify=False)
            # Method returns true if valid
            return client.is_authenticated()
        except Exception as e:
            print(f"❌ Error validing vault token: {e}")
            return False
    elif role_id and secret_id:
        try:
            client = hvac.Client(url=vault_addr, session=get_session(), verify=False)
            client.auth.approle.login(role_id=role_id, secret_id=secret_id)
            # Method returns true if valid
            return client.is_authenticated()
        except Exception as e:
            print(f"❌ Error validating approle creds: {e}")
            return False
    else:
        print("❌ No vault token or approle credential provided.")
        return False


def main():
    print_formatted_text(HTML(style_banner))
    while True:
        service_completer = WordCompleter(["keyring", "vault", "exit"], ignore_case=True)
        service = (
            prompt(
                "🧰 Choose service to configure (keyring/vault/exit): ", completer=service_completer, style=option_style
            )
            .strip()
            .lower()
        )

        if service == "keyring":
            configure_keyring()
        elif service == "vault":
            configure_vault()
        elif service == "exit":
            print(
                "👋 Thank you for using the Credential Bridge Wizard."
            )
            sys.exit(0)
        else:
            print("ℹ️ Invalid selection. Please choose 'keyring' or 'vault'❗")
            continue


def configure_keyring():
    while True:
        action_completer = WordCompleter(["add", "update", "delete", "get", "back"], ignore_case=True)
        action = (
            prompt("🧰 Choose action (add/update/delete/get/back): ", completer=action_completer, style=option_style)
            .strip()
            .lower()
        )

        if action == "back":
            return
        elif action not in ["add", "update", "delete", "get", "back"]:
            print(f"ℹ️ Invalid selection: {action}. Please try again❗")
            continue

        service_name = prompt("⌨️ Enter Service Name: ", style=entry_style).strip()
        name = prompt("⌨️ Enter secret name: ", style=entry_style).strip()
        secret = None

        if action in ["add", "update"]:
            secret = prompt("⌨️ Enter secret: ", style=entry_style).strip()

        run_keyring_cli(action, service_name, name, secret)


def configure_vault():
    while True:
        auth_type_completer = WordCompleter(["vault_token", "approle", "back"], ignore_case=True)
        auth_type = (
            prompt(
                "🧰 Choose authentication type (vault_token/approle/back): ",
                completer=auth_type_completer,
                style=option_style,
            )
            .strip()
            .lower()
        )

        if auth_type == "back":
            return
        elif auth_type not in ["vault_token", "approle", "back"]:
            print(f"ℹ️ Invalid selection: {auth_type}. Please try again❗")
            continue

        # Get existing credentials
        vault_token, vault_role_id, vault_secret_id = get_vault_credentials()

        # Get vault address from environment or config
        import os
        vault_addr = os.getenv("VAULT_ADDR")
        if not vault_addr:
            from .utils import load_config
            config = load_config()
            vault_addr = config.get("vault_addr")

        if not vault_addr:
            vault_addr = prompt("⌨️ Enter Vault Address (e.g., https://vault.example.com): ", style=entry_style).strip()
            if vault_addr:
                config_data = load_config() if 'config' not in locals() else config
                config_data["vault_addr"] = vault_addr
                save_config(config_data)

        if auth_type == "vault_token" and not vault_token:
            vault_token = prompt("⌨️ Enter Vault Token: ", style=entry_style).strip()
            if is_vault_cred_valid(vault_addr=vault_addr, vault_token=vault_token):
                config_data = load_config()
                config_data["vault_token"] = vault_token
                save_config(config_data)
                print("👍 Vault token saved successfully.")
            else:
                print("ℹ️ Invalid Vault token. Please try again.")
                continue

        elif auth_type == "approle" and not (vault_role_id and vault_secret_id):
            vault_role_id = prompt("⌨️ Enter Role ID: ", style=entry_style).strip()
            vault_secret_id = prompt("⌨️ Enter Secret ID: ", style=entry_style).strip()
            if is_vault_cred_valid(vault_addr=vault_addr, role_id=vault_role_id, secret_id=vault_secret_id):
                config_data = load_config()
                config_data["vault_role_id"] = vault_role_id
                config_data["vault_secret_id"] = vault_secret_id
                save_config(config_data)
                print("👍 AppRole credentials saved successfully.")
            else:
                print("ℹ️ Invalid Role ID or Secret ID. Please try again.")
                continue
        else:
            if auth_type == "vault_token":
                if not is_vault_cred_valid(vault_addr=vault_addr, vault_token=vault_token):
                    print(
                        "📰 Existing Vault token is not valid or has expired. Please obtain a new Vault token from Vault UI:"
                    )
                    print(f"💻Vault Token: {vault_token}")
                    vault_token = prompt("⌨️ Enter Vault Token: ", style=entry_style).strip()
                    if is_vault_cred_valid(vault_addr=vault_addr, vault_token=vault_token):
                        config_data = load_config()
                        config_data["vault_token"] = vault_token
                        save_config(config_data)
                        print("👍 Vault token saved successfully.")
                    else:
                        print("ℹ️ Invalid Vault token. Please try again.")
                        continue
                else:
                    print("👍Existing Vault Token is still valid continuing...")

            if auth_type == "approle":
                if not is_vault_cred_valid(vault_addr=vault_addr, role_id=vault_role_id, secret_id=vault_secret_id):
                    print(
                        "📰 Existing Vault Approle Credentials are not valid or has expired. Please obtain a new role or secret id from Vault UI:"
                    )
                    print(f"💻 App Role ID: {vault_role_id}")
                    print(f"💻 App Secret ID: {vault_secret_id}")
                    vault_role_id = prompt("⌨️ Enter Role ID: ", style=entry_style).strip()
                    vault_secret_id = prompt("⌨️ Enter Secret ID: ", style=entry_style).strip()
                    if is_vault_cred_valid(vault_addr=vault_addr, role_id=vault_role_id, secret_id=vault_secret_id):
                        config_data = load_config()
                        config_data["vault_role_id"] = vault_role_id
                        config_data["vault_secret_id"] = vault_secret_id
                        save_config(config_data)
                        print("👍 AppRole credentials saved successfully.")
                    else:
                        print("ℹ️ Invalid Role ID or Secret ID. Please try again.")
                        continue
                else:
                    print("👍Existing Approle credentials are still valid continuing...")

        while True:
            action_completer = WordCompleter(
                [
                    "add",
                    "update",
                    "delete",
                    "get",
                    "list",
                    "read-metadata",
                    "delete-versions",
                    "undelete-versions",
                    "destroy-versions",
                    "get-config",
                    "back",
                ],
                ignore_case=True,
            )
            action = (
                prompt(
                    "🧰 Choose action (add/update/delete/get/list/read-metadata/delete-versions/undelete-versions/destroy-versions/back): ",
                    completer=action_completer,
                    style=option_style,
                )
                .strip()
                .lower()
            )

            if action == "back":
                return
            elif action not in [
                "add",
                "update",
                "delete",
                "get",
                "list",
                "read-metadata",
                "delete-versions",
                "undelete-versions",
                "destroy-versions",
                "get-config",
                "back",
            ]:
                print(f"ℹ️ Invalid selection: {action}. Please try again❗")
                continue

            service_name = prompt("⌨️ Enter Service Name: ", style=entry_style).strip()

            secret_data = {}
            versions = None

            if action in ["add", "update"]:
                while True:
                    try:
                        num_secrets = int(
                            prompt(
                                f"⌨️ Enter the number of secrets to add for {service_name}: ", style=entry_style
                            ).strip()
                        )
                        break
                    except ValueError:
                        print("ℹ️ Invalid input. PLease enter a numeric value.")

                for _ in range(num_secrets):
                    secret_name = prompt("⌨️ Enter Secret Name: ", style=entry_style).strip()
                    secret_value = prompt("⌨️ Enter Secret Value: ", style=entry_style).strip()
                    secret_data[secret_name] = secret_value

            if action in [
                "list",
                "get-config",
                "read-metadata",
                "delete-versions",
                "undelete-versions",
                "destroy-versions",
            ]:
                ...

            if action in ["delete-versions", "undelete-versions", "destroy-versions"]:
                versions = []
                while True:
                    try:
                        num_versions = int(
                            prompt(
                                "⌨️ Enter the number of versions to delete/undelete/destroy: ", style=entry_style
                            ).strip()
                        )
                        for _ in range(num_versions):
                            version = int(prompt("⌨️ Enter version number: ", style=entry_style).strip())
                            versions.append(version)
                        break
                    except ValueError:
                        print("ℹ️ Invalid input. Please enter numeric values for versions.")

            run_vault_cli(action, service_name, secret_data, versions)


def run_keyring_cli(action, service_name, name, secret):
    manager = KeyringManager(service_name=service_name)
    keyring_handle(manager, action, service_name, name, secret)


def run_vault_cli(action, service_name, secret_data, versions=None):
    manager = VaultManager(service_name=service_name)
    vault_handle(manager, action, service_name, secret_data, versions)


if __name__ == "__main__":
    main()
