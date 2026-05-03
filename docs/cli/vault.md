# Vault CLI

Manage secrets in HashiCorp Vault KV-v2.

## Invocation

```bash
cb vault [COMMAND] [OPTIONS]
python -m credential_bridge vault [COMMAND] [OPTIONS]
python -m credential_bridge.cli.vault_cli [COMMAND] [OPTIONS]
```

## Authentication options

These apply to every subcommand. Set them as env vars to avoid repeating them:

| Flag | Env var | Default | Description |
|---|---|---|---|
| `--vault-url URL` | `VAULT_ADDR` | — | Vault server URL |
| `--vault-token TOKEN` | `VAULT_TOKEN` | — | Token authentication |
| `--vault-role-id ID` | `VAULT_ROLE_ID` | — | AppRole role ID |
| `--vault-secret-id ID` | `VAULT_SECRET_ID` | — | AppRole secret ID |
| `--service-name NAME` | — | `default_service` | Logging tag |
| `--mount-point MP` | — | `secret` | KV-v2 mount point |

Setting env vars once:

```bash
export VAULT_ADDR=https://vault.example.com
export VAULT_TOKEN=s.your-token
# Now all commands work without --vault-url / --vault-token
```

---

## add

Add a secret. Creates a new KV-v2 version if the path already exists.

### Syntax

```
cb vault add NAME [--secret KEY=VALUE]... [AUTH OPTIONS]
```

### Flags

| Flag | Short | Required | Description |
|---|---|---|---|
| `NAME` | — | Yes | Secret path, e.g. `myapp/database` |
| `--secret KEY=VALUE` | `-s` | Yes (or interactive) | Key-value pair (repeatable) |
| `--vault-url URL` | — | See auth options | Vault server URL |
| `--vault-token TOKEN` | — | See auth options | Token authentication |
| `--vault-role-id ID` | — | See auth options | AppRole role ID |
| `--vault-secret-id ID` | — | See auth options | AppRole secret ID |
| `--service-name NAME` | — | No | Logging tag (default: `default_service`) |
| `--mount-point MP` | — | No | KV-v2 mount point (default: `secret`) |

### Examples

```bash
# Single field, credentials via flags
cb vault add myapp/database \
  --secret user=admin \
  --vault-url https://vault.example.com \
  --vault-token s.your-token

# Multiple fields using short flag; credentials via env vars
export VAULT_ADDR=https://vault.example.com
export VAULT_TOKEN=s.your-token
cb vault add myapp/database --secret user=admin --secret pass=s3cr3t

# AppRole authentication
cb vault add myapp/api-keys \
  --secret key=sk-abc --secret secret=sk-secret \
  --vault-url https://vault.example.com \
  --vault-role-id my-role \
  --vault-secret-id my-secret-id

# Different mount point
cb vault add myapp/db --secret user=admin --mount-point kvv2

# Interactive (prompted when --secret is omitted)
cb vault add myapp/database
```

### Interactive prompt

When `--secret` is omitted the CLI prompts for key-value pairs with masked value input:

```
Enter secrets interactively. Leave KEY blank to finish.
  Key   : user
  Value : ········
  Key   : pass
  Value : ········
  Key   :
✓  Secret myapp/database added.
```

### Error scenarios

| Situation | Message | Resolution |
|---|---|---|
| Missing URL or credentials | `Configuration Error` | Set `VAULT_ADDR` and `VAULT_TOKEN` (or AppRole vars) |
| No key-value pairs provided | `Missing Input` | Pass at least one `--secret KEY=VALUE` |

---

## get

Retrieve a secret from Vault.

### Syntax

```
cb vault get NAME [--output FORMAT] [AUTH OPTIONS]
```

### Flags

| Flag | Short | Default | Description |
|---|---|---|---|
| `NAME` | — | — | Secret path |
| `--output FORMAT` | `-o` | `rich` | Output format: `rich` or `json` |
| `--vault-url URL` | — | `$VAULT_ADDR` | Vault server URL |
| `--vault-token TOKEN` | — | `$VAULT_TOKEN` | Token authentication |
| `--vault-role-id ID` | — | `$VAULT_ROLE_ID` | AppRole role ID |
| `--vault-secret-id ID` | — | `$VAULT_SECRET_ID` | AppRole secret ID |
| `--service-name NAME` | — | `default_service` | Logging tag |
| `--mount-point MP` | — | `secret` | KV-v2 mount point |

### Examples

```bash
# Rich panel output (default)
cb vault get myapp/database

# JSON output for scripting
cb vault get myapp/database --output json
cb vault get myapp/database -o json | jq '.user'

# Parse a single field in a shell script
USER=$(cb vault get myapp/database -o json | jq -r '.user')
```

### Error scenarios

| Situation | Message | Resolution |
|---|---|---|
| Secret path not found | `Not Found` | Check path with `cb vault list` |
| Auth failure | `VaultAuthError` | Renew token or verify AppRole credentials |
| Server unreachable | `VaultConnectionError` | Check `VAULT_ADDR` and network |

---

## update

Update an existing secret. Creates a new version in KV-v2; prior versions are retained.

### Syntax

```
cb vault update NAME [--secret KEY=VALUE]... [AUTH OPTIONS]
```

### Flags

| Flag | Short | Required | Description |
|---|---|---|---|
| `NAME` | — | Yes | Secret path |
| `--secret KEY=VALUE` | `-s` | Yes (or interactive) | Key-value pair (repeatable) |
| `--vault-url URL` | — | See auth options | Vault server URL |
| `--vault-token TOKEN` | — | See auth options | Token authentication |
| `--vault-role-id ID` | — | See auth options | AppRole role ID |
| `--vault-secret-id ID` | — | See auth options | AppRole secret ID |
| `--service-name NAME` | — | No | Logging tag (default: `default_service`) |
| `--mount-point MP` | — | No | KV-v2 mount point (default: `secret`) |

### Examples

```bash
# Update a single field
cb vault update myapp/database --secret pass=new_password

# Update multiple fields at once
cb vault update myapp/database --secret pass=new_password --secret user=new_user

# Interactive (prompted when --secret is omitted)
cb vault update myapp/database
```

### Error scenarios

| Situation | Message | Resolution |
|---|---|---|
| Secret path not found | `Not Found` | Use `cb vault add` to create it first |
| Missing URL or credentials | `Configuration Error` | Set `VAULT_ADDR` / `VAULT_TOKEN` |

---

## delete

Permanently delete a secret and all its versions.

!!! danger "Irreversible"
    This deletes all KV-v2 versions of the secret. There is no undo.

### Syntax

```
cb vault delete NAME [--yes] [AUTH OPTIONS]
```

### Flags

| Flag | Short | Default | Description |
|---|---|---|---|
| `NAME` | — | — | Secret path |
| `--yes` | `-y` | `False` | Skip confirmation prompt |
| `--vault-url URL` | — | `$VAULT_ADDR` | Vault server URL |
| `--vault-token TOKEN` | — | `$VAULT_TOKEN` | Token authentication |
| `--vault-role-id ID` | — | `$VAULT_ROLE_ID` | AppRole role ID |
| `--vault-secret-id ID` | — | `$VAULT_SECRET_ID` | AppRole secret ID |
| `--service-name NAME` | — | `default_service` | Logging tag |
| `--mount-point MP` | — | `secret` | KV-v2 mount point |

### Examples

```bash
# Interactive confirmation
cb vault delete myapp/database

# Skip confirmation (CI/scripting)
cb vault delete myapp/database --yes

# Short flag
cb vault delete myapp/database -y
```

### Error scenarios

| Situation | Message | Resolution |
|---|---|---|
| Secret path not found | `Not Found` | Verify path with `cb vault list` |
| Auth failure | `VaultAuthError` | Renew token or verify AppRole credentials |

---

## list

List secret keys at a path prefix within the mount point.

### Syntax

```
cb vault list [PATH] [AUTH OPTIONS]
```

### Flags

| Flag | Short | Default | Description |
|---|---|---|---|
| `PATH` | — | `""` (mount root) | Path prefix to list |
| `--vault-url URL` | — | `$VAULT_ADDR` | Vault server URL |
| `--vault-token TOKEN` | — | `$VAULT_TOKEN` | Token authentication |
| `--vault-role-id ID` | — | `$VAULT_ROLE_ID` | AppRole role ID |
| `--vault-secret-id ID` | — | `$VAULT_SECRET_ID` | AppRole secret ID |
| `--service-name NAME` | — | `default_service` | Logging tag |
| `--mount-point MP` | — | `secret` | KV-v2 mount point |

### Examples

```bash
# List root of mount_point
cb vault list

# List secrets under myapp/
cb vault list myapp/

# List a nested path
cb vault list myapp/database/

# List using a custom mount point
cb vault list --mount-point kvv2
```

!!! note "No --output json for list"
    The `list` subcommand renders a Rich table. Pipe through a script or use
    `cb vault get` with `-o json` for machine-readable secret values.

### Error scenarios

| Situation | Message | Resolution |
|---|---|---|
| Path not found | `CredentialBridgeError` | Verify path prefix exists |
| Auth failure | `VaultAuthError` | Renew token or verify AppRole credentials |
| Server unreachable | `VaultConnectionError` | Check `VAULT_ADDR` and network |

---

## Error reference

| Error | Cause | Fix |
|---|---|---|
| `Configuration Error` | Missing URL or credentials | Set `VAULT_ADDR` / `VAULT_TOKEN` |
| `VaultAuthError` | Bad token or expired | Renew token in Vault UI |
| `VaultConnectionError` | Server unreachable | Check `VAULT_ADDR` and network |
| `Not Found` | Secret path doesn't exist | Check path with `cb vault list` |
| `Missing Input` | No `--secret` pairs provided | Pass at least one `--secret KEY=VALUE` |
