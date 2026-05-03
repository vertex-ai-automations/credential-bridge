# System Keyring Backend

## When to use

`KeyringBackend` is the right choice when you need to store developer credentials
locally on a single machine without running any additional infrastructure. It
delegates storage to the OS credential manager, which provides hardware-backed or
OS-level encryption automatically. Common use cases include storing personal API
keys, OAuth tokens, or database passwords for CLI tools, desktop applications, and
local development workflows.

## Platform support

| Platform | Credential store | Notes |
|---|---|---|
| Windows | Windows Credential Manager | Built-in; no extra setup required |
| macOS | macOS Keychain | Built-in; no extra setup required |
| Linux (desktop) | GNOME Keyring / KWallet | Requires a running Secret Service daemon |
| Linux (headless) | Secret Service via D-Bus | Install `python3-secretstorage`; run GNOME Keyring or a compatible daemon |

!!! tip "Linux headless setup"
    On a headless Linux server, install the `secretstorage` library and launch a
    D-Bus Secret Service:
    ```bash
    pip install secretstorage
    # Then start a Secret Service daemon such as GNOME Keyring in headless mode
    ```

## Constructor parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `service_name` | `str` | `"default_service"` | Groups all secrets under this namespace in the OS credential store. |
| `log_level` | `LogLevel \| str` | `LogLevel.WARNING` | Minimum log level for the internal logger. |
| `logger` | `PyLogShield \| None` | `None` | Provide your own `PyLogShield` logger instance. |
| `mask` | `bool` | `True` | Mask secret values in log output. |

!!! warning "Default service name differs between library and CLI"
    `KeyringBackend()` defaults `service_name` to `"default_service"`, but the CLI
    (`cb keyring`) defaults `--service-name` to `"default"`. A secret written with one
    using its default is invisible to the other. Always pass `service_name=` /
    `--service-name` explicitly to ensure portability.

## JSON serialisation

All secrets are stored as **JSON strings** in the keyring. When you call
`add_secret("key", {"field": "value"})`, the dict is serialised with
`json.dumps()` before being written. On retrieval, `get_secret()` deserialises
the string back to a dict with `json.loads()`. This means any JSON-serialisable
dict round-trips transparently, including multi-field secrets.

```python
# What gets stored in the OS keyring:
# service: "myapp", username: "database"
# password: '{"host": "localhost", "port": "5432", "user": "admin"}'

# What you get back:
secret = backend.get_secret("database")
# {"host": "localhost", "port": "5432", "user": "admin"}
```

## CRUD operations

### add_secret

Stores a new secret. Raises `KeyringError` if the key already exists — use
`update_secret()` to change an existing entry.

```python
from credential_bridge import KeyringBackend

backend = KeyringBackend(service_name="myapp")

# Single-field secret
backend.add_secret("github_token", {"github_token": "ghp_xxx"})
```

CLI equivalent:

```bash
cb keyring add github_token --secret github_token=ghp_xxx --service-name myapp
```

### get_secret

Returns the secret dict. Raises `KeyringError` if the key does not exist.

```python
secret = backend.get_secret("github_token")
# {"github_token": "ghp_xxx"}
print(secret["github_token"])  # ghp_xxx
```

CLI equivalent:

```bash
cb keyring get github_token --service-name myapp
```

### update_secret

Replaces the stored value for an existing key. Raises `KeyringError` if the key
does not exist — use `add_secret()` first.

```python
backend.update_secret("github_token", {"github_token": "ghp_new"})
```

CLI equivalent:

```bash
cb keyring update github_token --secret github_token=ghp_new --service-name myapp
```

### delete_secret

Removes a secret from the keyring. Raises `KeyringError` if the key does not
exist.

```python
backend.delete_secret("github_token")
```

CLI equivalent:

```bash
cb keyring delete github_token --service-name myapp --yes
```

### list_secrets

!!! warning "Not supported on any platform"
    `list_secrets()` always raises `KeyringError`. Windows Credential Manager and
    macOS Keychain do not expose enumeration APIs — there is no supported way to
    retrieve all keys under a service name. Keep track of your key names
    separately (e.g. in application configuration or documentation).

```python
from credential_bridge import KeyringError

try:
    keys = backend.list_secrets()
except KeyringError as e:
    print(e)
    # KeyringBackend.list_secrets() is not supported on this platform.
    # Windows Credential Manager and macOS Keychain do not expose enumeration APIs.
```

## Multi-field secrets

Store any number of key-value pairs under a single keyring entry. The entire dict
is serialised as one JSON string.

```python
backend.add_secret(
    "database",
    {"host": "localhost", "port": "5432", "user": "admin"},
)

secret = backend.get_secret("database")
# {"host": "localhost", "port": "5432", "user": "admin"}

print(secret["host"])  # localhost
print(secret["port"])  # 5432
```

## Error handling

```python
from credential_bridge import KeyringError

try:
    backend.add_secret("github_token", {"github_token": "ghp_xxx"})
except KeyringError as e:
    # Raised when key already exists
    print(f"Keyring error: {e}")

try:
    secret = backend.get_secret("missing_key")
except KeyringError as e:
    # Raised when key is not found
    print(f"Not found: {e}")
```

### Common errors

| Exception | Cause | Resolution |
|---|---|---|
| `KeyringError: already exists` | `add_secret()` called on an existing key | Use `update_secret()` to change the value |
| `KeyringError: does not exist` | `update_secret()` called on a missing key | Use `add_secret()` first |
| `KeyringError: not found` | `get_secret()` or `delete_secret()` on a missing key | Verify the key name |
| `KeyringError: not supported` | `list_secrets()` called | Platform limitation — track key names manually |
| `ConfigurationError` | `logger` argument is not a `PyLogShield` instance | Pass a valid `PyLogShield` instance |

`KeyringError` is a subclass of `BackendError`.
