# Quick Start

## 1. Install

```bash
pip install credential-bridge
```

## 2. Choose a backend

=== ".env File (simplest)"

    No server required. Great for local development.

    ```python
    from credential_bridge import SecretsManager

    sm = SecretsManager("env", path=".env")
    # "database" is a comment label; get_secret uses the actual key name
    sm.add_secret("database", {"DB_HOST": "localhost", "DB_PORT": "5432"})

    result = sm.get_secret("DB_HOST")   # not sm.get_secret("database")
    print(result["DB_HOST"])  # localhost
    ```

    Note: for `.env` files, `get_secret` takes the individual env var key (`DB_HOST`), not the group label (`database`) used in `add_secret`. See [.env File backend](../backends/env-file/) for details.

    Via CLI:
    ```bash
    cb env add database --secret DB_HOST=localhost --secret DB_PORT=5432
    cb env get DB_HOST
    cb env list
    ```

=== "System Keyring"

    OS-encrypted local credential storage.

    ```python
    from credential_bridge import SecretsManager

    sm = SecretsManager("keyring", service_name="myapp")
    sm.add_secret("github_token", {"github_token": "ghp_abc123"})

    result = sm.get_secret("github_token")
    print(result["github_token"])  # ghp_abc123
    ```

    Via CLI:
    ```bash
    cb keyring add github_token --secret github_token=ghp_abc123 -s myapp
    cb keyring get github_token -s myapp
    ```

=== "HashiCorp Vault"

    Production-grade centralised secrets. Set `VAULT_ADDR` first.

    ```bash
    export VAULT_ADDR=https://vault.example.com
    export VAULT_TOKEN=s.your-token
    ```

    ```python
    from credential_bridge import SecretsManager

    sm = SecretsManager("vault")   # reads from env vars
    sm.add_secret("myapp/database", {"user": "admin", "pass": "s3cr3t"})

    result = sm.get_secret("myapp/database")
    print(result["user"])  # admin
    ```

    Via CLI:
    ```bash
    cb vault add myapp/database --secret user=admin --secret pass=s3cr3t
    cb vault get myapp/database
    ```

## 3. Handle errors

```python
from credential_bridge import (
    SecretsManager,
    CredentialBridgeError,
    VaultSecretNotFoundError,
    EnvFileNotFoundError,
)

sm = SecretsManager("env", path=".env")

try:
    result = sm.get_secret("MISSING_KEY")
except EnvFileNotFoundError:
    print("Key not in .env file")
except CredentialBridgeError as e:
    print(f"Error: {e}")
```

## 4. Switch backends with no code changes

The same five methods work across all backends:

```python
# Development
sm = SecretsManager("env", path=".env")

# Staging
sm = SecretsManager("keyring", service_name="myapp-staging")

# Production — just change the constructor
sm = SecretsManager("vault", vault_url="https://vault.example.com", vault_token="s.xxx")

# The rest of your code is identical
result = sm.get_secret("myapp/database")
```

## 5. Try the interactive wizard

```bash
cb wizard
```

The wizard guides you through all operations with tab-completion and masked secret input.

## What's next?

- [Backend comparison](../backends/comparison/) — which backend fits your use case
- [SecretsManager](../secrets-manager.md) — facade API and custom backends
- [CLI reference](../cli/cb/) — all commands and flags
