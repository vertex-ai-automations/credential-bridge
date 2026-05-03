# Keyring CLI

Manage secrets in the OS credential store (Windows Credential Manager, macOS Keychain, Linux Secret Service).

## Invocation

```bash
cb keyring [COMMAND] [OPTIONS]
python -m credential_bridge keyring [COMMAND] [OPTIONS]
python -m credential_bridge.cli.keyring_cli [COMMAND] [OPTIONS]
```

## Options

| Flag | Short | Default | Description |
|---|---|---|---|
| `--service-name NAME` | `-s` | `default` | Keyring service namespace |

The service name acts as a namespace so secrets from different applications can share the same key name without collision.

---

## add

Store a new secret in the OS keyring. Fails if the key already exists under the given service name.

### Syntax

```
cb keyring add NAME [--secret KEY=VALUE]... [--service-name NAME]
```

### Flags

| Flag | Short | Required | Description |
|---|---|---|---|
| `NAME` | — | Yes | Key name to store |
| `--secret KEY=VALUE` | — | Yes (or interactive) | Key-value pair (repeatable) |
| `--service-name NAME` | `-s` | No | Service namespace (default: `default`) |

### Examples

```bash
# Single field, default service
cb keyring add github_token --secret github_token=ghp_xxx

# Single field, named service
cb keyring add github_token -s myapp --secret github_token=ghp_xxx

# Multi-field secret (stored as JSON internally)
cb keyring add database --secret host=localhost --secret port=5432

# Interactive (prompted when --secret is omitted)
cb keyring add github_token -s myapp
```

### Interactive prompt

When `--secret` is omitted the CLI prompts for key-value pairs with masked value input:

```
Enter secrets interactively. Leave KEY blank to finish.
  Key   : github_token
  Value : ········
  Key   :
✓  Secret github_token added.
```

!!! info "Key already exists"
    `add` raises an error if the key already exists under the service name. Use `update` to change an existing value.

---

## get

Retrieve a secret from the OS keyring.

### Syntax

```
cb keyring get NAME [--output FORMAT] [--service-name NAME]
```

### Flags

| Flag | Short | Default | Description |
|---|---|---|---|
| `NAME` | — | — | Key name |
| `--output FORMAT` | `-o` | `rich` | Output format: `rich` or `json` |
| `--service-name NAME` | `-s` | `default` | Service namespace |

### Examples

```bash
# Rich output (default)
cb keyring get github_token -s myapp

# JSON output
cb keyring get github_token -s myapp --output json

# Extract a single field with jq
cb keyring get database -s myapp -o json | jq '.host'
```

### Error scenarios

| Situation | Message | Resolution |
|---|---|---|
| Key not found | `CredentialBridgeError` | Verify the key name and service name match exactly what was used when the secret was added. `cb keyring list` is not supported — use `cb keyring get <name>` if you know the key name. |
| Backend unavailable (Linux) | `CredentialBridgeError` | Ensure a D-Bus Secret Service (e.g. `gnome-keyring`) is running |

---

## update

Replace the value of an existing keyring entry. Fails if the key does not exist.

### Syntax

```
cb keyring update NAME [--secret KEY=VALUE]... [--service-name NAME]
```

### Flags

| Flag | Short | Required | Description |
|---|---|---|---|
| `NAME` | — | Yes | Key name |
| `--secret KEY=VALUE` | — | Yes (or interactive) | New key-value pair (repeatable) |
| `--service-name NAME` | `-s` | No | Service namespace (default: `default`) |

### Examples

```bash
# Update a single field
cb keyring update github_token --secret github_token=ghp_new -s myapp

# Update multiple fields
cb keyring update database --secret host=prod.db.example.com --secret port=5433

# Interactive (prompted when --secret is omitted)
cb keyring update github_token -s myapp
```

---

## delete

Remove a secret from the OS keyring.

### Syntax

```
cb keyring delete NAME [--yes] [--service-name NAME]
```

### Flags

| Flag | Short | Default | Description |
|---|---|---|---|
| `NAME` | — | — | Key name |
| `--yes` | `-y` | `False` | Skip confirmation prompt |
| `--service-name NAME` | `-s` | `default` | Service namespace |

### Examples

```bash
# With confirmation prompt
cb keyring delete github_token -s myapp

# Skip confirmation (CI/scripting)
cb keyring delete github_token -s myapp --yes

# Short flag
cb keyring delete github_token -s myapp -y
```

### Error scenarios

| Situation | Message | Resolution |
|---|---|---|
| Key not found | `CredentialBridgeError` | Verify name and service name |

---

!!! warning "list is not supported"
    `cb keyring list` is not available. Windows Credential Manager and macOS Keychain do not expose enumeration APIs. Use `cb keyring get KEY` to retrieve individual secrets by name.
