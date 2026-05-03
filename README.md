<a name="readme-top"></a>

<div align="center">
<img src="https://github.com/vertex-ai-automations/credential-bridge/raw/main/docs/img/credential-bridge.png" alt="Credential Bridge Logo" width="420">

<br/>

[![PyPI version](https://img.shields.io/pypi/v/credential-bridge?color=indigo&logo=pypi&logoColor=white)](https://pypi.org/project/credential-bridge/)
[![Python versions](https://img.shields.io/pypi/pyversions/credential-bridge?color=indigo&logo=python&logoColor=white)](https://pypi.org/project/credential-bridge/)
[![License: MIT](https://img.shields.io/badge/license-MIT-indigo.svg)](https://github.com/vertex-ai-automations/credential-bridge/blob/main/LICENSE.txt)

<br/>

<p>
<a href="https://vertex-ai-automations.github.io/credential-bridge"><strong>Documentation</strong></a>
&nbsp;·&nbsp;
<a href="https://github.com/vertex-ai-automations/credential-bridge/issues/new">Report Bug</a>
&nbsp;·&nbsp;
<a href="https://www.vertexaiautomations.com">Vertex AI Automations</a>
</p>

</div>

# credential-bridge

A unified Python library for secrets management across HashiCorp Vault, the OS system keyring, and `.env` files.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Usage](#cli-usage)
- [Backends](#backends)
- [Custom Backends](#custom-backends)
- [Error Handling](#error-handling)
- [Environment Variables](#environment-variables)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- **Three backends**: HashiCorp Vault (KV-v2), OS system keyring, and `.env` files
- **`SecretsManager` facade**: switch backends without changing application code
- **Plugin architecture**: register third-party backends with one call
- **Typed exceptions**: granular hierarchy rooted at `CredentialBridgeError`
- **Typer + Rich CLI**: `cb`, `vault-cli`, `keyring-cli`, `env-cli`, and `run-wizard` entry points
- **Cross-platform**: works on Linux, macOS, and Windows

---

## Installation

```bash
pip install credential-bridge

# With dev dependencies
pip install "credential-bridge[dev]"
```

---

## Quick Start

### Using SecretsManager

```python
from credential_bridge import SecretsManager

# HashiCorp Vault (set VAULT_ADDR env var first)
sm = SecretsManager("vault", vault_token="s.xxx")
sm.add_secret("myapp/database", {"user": "admin", "pass": "s3cr3t"})
secret = sm.get_secret("myapp/database")

# System keyring
sm = SecretsManager("keyring", service_name="myapp")
sm.add_secret("api_key", {"api_key": "sk-abc123"})

# .env file
sm = SecretsManager("env", path=".env")
sm.add_secret("DATABASE", {"DB_HOST": "localhost", "DB_PORT": "5432"})
```

### Using backends directly

```python
from credential_bridge import VaultBackend, KeyringBackend, EnvFileBackend

# Vault with AppRole auth
vault = VaultBackend(
    vault_url="https://vault.example.com",
    vault_role_id="<role-id>",
    vault_secret_id="<secret-id>",
)
vault.add_secret("myapp/db", {"password": "hunter2"})

# Keyring
kr = KeyringBackend(service_name="myapp")
kr.add_secret("token", {"value": "sk-abc123"})

# .env file
env = EnvFileBackend(path=".env")
env.add_secret("DATABASE", {"DB_HOST": "localhost", "DB_PORT": "5432"})
```

---

## CLI Usage

```bash
# Show all commands
cb --help

# Vault
cb vault add myapp/db --secret user=admin --secret pass=s3cr3t
cb vault get myapp/db
cb vault list
cb vault delete myapp/db

# Keyring
cb keyring add api_key --secret api_key=sk-abc123 --service-name myapp
cb keyring get api_key --service-name myapp
cb keyring delete api_key --service-name myapp

# .env file
cb env add DATABASE --secret DB_HOST=localhost --secret DB_PORT=5432
cb env get DB_HOST
cb env list
cb env delete DB_HOST

# Interactive wizard
cb wizard
```

---

## Backends

| Backend | Best use case |
|---------|---------------|
| **Vault** | Production workloads requiring audit logs, dynamic secrets, fine-grained policies, and centralized governance |
| **Keyring** | Developer machines and CI environments where OS-level credential storage is available |
| **.env file** | Local development, Docker Compose setups, and twelve-factor apps that read config from the environment |

---

## Custom Backends

Implement `BaseSecretBackend` and register it with `SecretsManager`:

```python
from credential_bridge import BaseSecretBackend, SecretsManager
from credential_bridge.manager import register_backend
from typing import Any, Dict, List

class RedisBackend(BaseSecretBackend):
    backend_name = "redis"  # required — omitting raises TypeError

    def add_secret(self, name: str, secret: Dict[str, Any]) -> None: ...
    def get_secret(self, name: str) -> Dict[str, Any]: ...
    def update_secret(self, name: str, secret: Dict[str, Any]) -> None: ...
    def delete_secret(self, name: str) -> None: ...
    def list_secrets(self, path: str = "") -> List[str]: ...

register_backend("redis", RedisBackend)

sm = SecretsManager("redis", host="localhost", port=6379)
```

---

## Error Handling

All exceptions inherit from `CredentialBridgeError`:

```
CredentialBridgeError
├── BackendError
│   ├── VaultError
│   │   ├── VaultAuthError          — bad token / AppRole credentials
│   │   ├── VaultConnectionError    — unreachable server
│   │   └── VaultSecretNotFoundError — secret path does not exist
│   ├── KeyringError
│   └── EnvFileError
│       ├── EnvFileNotFoundError    — key not found
│       └── EnvFileKeyExistsError   — add_secret called on existing key
├── BackendNotRegisteredError
└── ConfigurationError
```

```python
from credential_bridge import (
    SecretsManager,
    VaultAuthError,
    VaultConnectionError,
    VaultSecretNotFoundError,
    CredentialBridgeError,
)

sm = SecretsManager("vault", vault_token="s.xxx")

try:
    secret = sm.get_secret("myapp/database")
except VaultSecretNotFoundError:
    print("Secret path does not exist")
except VaultAuthError:
    print("Authentication failed — check your token or AppRole credentials")
except VaultConnectionError:
    print("Could not reach Vault — check VAULT_ADDR")
except CredentialBridgeError as exc:
    print(f"Unexpected error: {exc}")
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `VAULT_ADDR` | Vault server URL (e.g. `https://vault.example.com`) |
| `VAULT_TOKEN` | Token for Token auth method |
| `VAULT_ROLE_ID` | Role ID for AppRole auth method |
| `VAULT_SECRET_ID` | Secret ID for AppRole auth method |

Resolution order for `VaultBackend`: constructor argument → environment variable → `~/.vault_config.json`.

---

## Development

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run unit tests
pytest tests/unit/

# Run integration tests (requires external services)
pytest tests/integration/ -m integration

# Lint
ruff check src/

# Type check
mypy src/

# Serve docs locally
mkdocs serve
```

---

## Contributing

All contributions are welcome! Fork the repo, make your changes, and open a pull request. You can also open an issue with the label `enhancement`.

[View all contributors](https://github.com/vertex-ai-automations/credential-bridge/graphs/contributors)

---

## License

MIT — see [LICENSE.txt](LICENSE.txt) for details.

<p align="right">(<a href="#readme-top">back to top</a>)</p>
