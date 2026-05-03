# import subprocess
import sys

from prompt_toolkit import print_formatted_text, prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style

from .utils import get_vault_credentials, load_welcome_banner, load_config, save_config

welcome_banner = load_welcome_banner("welcome_banner.txt")

style_banner = f"<b><yellow>{welcome_banner}</yellow></b>"

option_style = Style.from_dict({"prompt": "fg:ansibrightcyan bold"})
entry_style = Style.from_dict({"prompt": "fg:ansibrightgreen bold"})


def is_vault_cred_valid(vault_token=None, role_id=None, secret_id=None):
    """Validate Vault credentials by attempting authentication through VaultBackend."""
    import os
    vault_addr = os.environ.get("VAULT_ADDR", "")
    if not vault_addr:
        print("❌ VAULT_ADDR environment variable not set.")
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
            print("❌ No credentials provided.")
            return False
        SecretsManager("vault", **kwargs)
        return True
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return False


def main():
    print_formatted_text(HTML(style_banner))
    while True:
        service_completer = WordCompleter(["keyring", "vault", "env", "exit"], ignore_case=True)
        service = (
            prompt(
                "🧰 Choose service (keyring/vault/env/exit): ",
                completer=service_completer,
                style=option_style,
            )
            .strip()
            .lower()
        )

        if service == "keyring":
            configure_keyring()
        elif service == "vault":
            configure_vault()
        elif service == "env":
            configure_env()
        elif service == "exit":
            print(
                "👋 Thank you for using the Credential Bridge Wizard."
            )
            sys.exit(0)
        else:
            print("ℹ️ Invalid selection. Please choose 'keyring', 'vault', or 'env'❗")
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

        if auth_type == "vault_token" and not vault_token:
            vault_token = prompt("⌨️ Enter Vault Token: ", style=entry_style).strip()
            if is_vault_cred_valid(vault_token=vault_token):
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
            if is_vault_cred_valid(role_id=vault_role_id, secret_id=vault_secret_id):
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
                if not is_vault_cred_valid(vault_token=vault_token):
                    print(
                        "📰 Existing Vault token is not valid or has expired. Please obtain a new Vault token from Vault UI:"
                    )
                    print(f"💻 Existing Vault Token: ...{vault_token[-4:]}")
                    vault_token = prompt("⌨️ Enter Vault Token: ", style=entry_style).strip()
                    if is_vault_cred_valid(vault_token=vault_token):
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
                if not is_vault_cred_valid(role_id=vault_role_id, secret_id=vault_secret_id):
                    print(
                        "📰 Existing Vault Approle Credentials are not valid or has expired. Please obtain a new role or secret id from Vault UI:"
                    )
                    print(f"💻 Existing Role ID: ...{vault_role_id[-4:]}")
                    print(f"💻 Existing Secret ID: ...{vault_secret_id[-4:]}")
                    vault_role_id = prompt("⌨️ Enter Role ID: ", style=entry_style).strip()
                    vault_secret_id = prompt("⌨️ Enter Secret ID: ", style=entry_style).strip()
                    if is_vault_cred_valid(role_id=vault_role_id, secret_id=vault_secret_id):
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

            service_name = prompt("⌨️ Enter Service Name (tag): ", style=entry_style).strip()
            secret_path = prompt("⌨️ Enter Secret Path (e.g. myapp/database): ", style=entry_style).strip()

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

            run_vault_cli(action, service_name, secret_path, secret_data, versions)


def configure_env():
    from .backends.env_file import EnvFileBackend
    while True:
        action_completer = WordCompleter(["add", "get", "update", "delete", "list", "back"], ignore_case=True)
        action = (
            prompt("🧰 Choose action (add/get/update/delete/list/back): ",
                   completer=action_completer, style=option_style)
            .strip().lower()
        )
        if action == "back":
            return
        env_path = prompt("⌨️ Enter .env file path (default: .env): ", style=entry_style).strip() or ".env"
        backend = EnvFileBackend(path=env_path)
        try:
            if action == "list":
                keys = backend.list_secrets()
                print(f"Keys in {env_path}: {keys}")
            elif action in ["add", "update"]:
                name = prompt("⌨️ Enter key name: ", style=entry_style).strip()
                value = prompt("⌨️ Enter value: ", style=entry_style).strip()
                if action == "add":
                    backend.add_secret(name, {name: value})
                else:
                    backend.update_secret(name, {name: value})
                print(f"👍 {action.capitalize()} successful.")
            elif action in ["get", "delete"]:
                name = prompt("⌨️ Enter key name: ", style=entry_style).strip()
                if action == "get":
                    result = backend.get_secret(name)
                    print(f"👍 {name} = {result.get(name)}")
                else:
                    backend.delete_secret(name)
                    print(f"👍 {name} deleted.")
        except Exception as e:
            print(f"❌ Error: {e}")


def run_keyring_cli(action, service_name, name, secret):
    from .manager import SecretsManager
    manager = SecretsManager("keyring", service_name=service_name)
    try:
        if action == "add":
            manager.add_secret(name, {name: secret})
            print(f"👍 Added: {service_name} / {name}")
        elif action == "get":
            result = manager.get_secret(name)
            print(f"👍 {name} = {result.get(name)}")
        elif action == "update":
            manager.update_secret(name, {name: secret})
            print(f"👍 Updated: {service_name} / {name}")
        elif action == "delete":
            manager.delete_secret(name)
            print(f"👍 Deleted: {service_name} / {name}")
    except Exception as e:
        print(f"❌ Error: {e}")


def run_vault_cli(action, service_name, secret_path, secret_data, versions=None):
    from .manager import SecretsManager
    manager = SecretsManager("vault", service_name=service_name)
    try:
        if action == "add":
            manager.add_secret(secret_path, secret_data)
            print(f"👍 Added: {secret_path}")
        elif action == "get":
            result = manager.get_secret(secret_path)
            print(f"👍 {secret_path}: {result}")
        elif action == "update":
            manager.update_secret(secret_path, secret_data)
            print(f"👍 Updated: {secret_path}")
        elif action == "delete":
            manager.delete_secret(secret_path)
            print(f"👍 Deleted: {secret_path}")
        elif action == "list":
            keys = manager.list_secrets(secret_path)
            print(f"👍 Keys: {keys}")
        elif action in ("read-metadata", "delete-versions", "undelete-versions", "destroy-versions", "get-config"):
            vault_backend = manager.backend
            if action == "read-metadata":
                meta = vault_backend.read_secret_metadata(secret_path)
                print(f"👍 Metadata: {meta}")
            elif action == "delete-versions":
                vault_backend.delete_secret_versions(secret_path, versions)
                print(f"👍 Deleted versions {versions} of {secret_path}")
            elif action == "undelete-versions":
                vault_backend.undelete_secret_versions(secret_path, versions)
                print(f"👍 Undeleted versions {versions} of {secret_path}")
            elif action == "destroy-versions":
                vault_backend.destroy_secret_versions(secret_path, versions)
                print(f"👍 Destroyed versions {versions} of {secret_path}")
            elif action == "get-config":
                cfg = vault_backend.get_config()
                print(f"👍 Config: {cfg}")
        print(f"👍 {action} completed.")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
