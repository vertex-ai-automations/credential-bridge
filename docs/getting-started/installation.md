# Installation

## Requirements

- Python 3.8+
- pip

## Install from PyPI

```bash
pip install credential-bridge
```

## Development install

```bash
git clone https://github.com/vertex-ai-automations/credential-bridge
cd credential-bridge
pip install -e ".[dev]"
```

## Optional extras

```bash
pip install "credential-bridge[dev]"     # pytest, mypy, ruff
pip install "credential-bridge[docs]"    # documentation build dependencies
```

## Verify installation

```bash
cb --version
cb --help
```

## Invocation methods

The `cb` command is the primary entry point. If your organisation blocks executable installation, use the `python -m` fallback — it runs identically:

| Installed command | `python -m` equivalent |
|---|---|
| `cb` | `python -m credential_bridge` |
| `cb vault …` | `python -m credential_bridge.cli.vault_cli …` |
| `cb keyring …` | `python -m credential_bridge.cli.keyring_cli …` |
| `cb env …` | `python -m credential_bridge.cli.env_cli …` |

```bash
# These are identical:
cb env list --path .env
python -m credential_bridge env list --path .env
python -m credential_bridge.cli.env_cli list --path .env
```

## Backend prerequisites

=== "HashiCorp Vault"
    Set `VAULT_ADDR` before using the vault backend:
    ```bash
    export VAULT_ADDR=https://vault.example.com   # Linux/macOS
    $env:VAULT_ADDR = "https://vault.example.com" # PowerShell
    ```
    Have either a **token** (`VAULT_TOKEN`) or **AppRole** credentials ready.

=== "System Keyring"
    - **Windows**: Windows Credential Manager (built-in)
    - **macOS**: macOS Keychain (built-in)
    - **Linux**: Install `python3-secretstorage` and ensure a D-Bus Secret Service is running:
      ```bash
      sudo apt install python3-secretstorage gnome-keyring
      ```

=== ".env File"
    No prerequisites — just a writable directory.

    !!! warning "Never commit .env to git"
        Add `.env` to `.gitignore` before creating it.
