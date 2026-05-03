# .env File CLI

Manage secrets in a `.env` file.

## Invocation

```bash
cb env [COMMAND] [OPTIONS]
python -m credential_bridge env [COMMAND] [OPTIONS]
python -m credential_bridge.cli.env_cli [COMMAND] [OPTIONS]
```

## Options

| Flag | Short | Default | Description |
|---|---|---|---|
| `--path PATH` | `-p` | `.env` | Path to the .env file |

---

## add

Add one or more key-value pairs to the `.env` file. Fails if any key already exists.

### Syntax

```
cb env add NAME [--secret KEY=VALUE]... [--path PATH]
```

### Flags

| Flag | Short | Required | Description |
|---|---|---|---|
| `NAME` | — | Yes | Group label / key name used as a comment header in the file |
| `--secret KEY=VALUE` | `-s` | Yes (or interactive) | Key-value pair (repeatable) |
| `--path PATH` | `-p` | No | Path to the .env file (default: `.env`) |

### Examples

```bash
# Single key, default .env
cb env add API_KEY --secret API_KEY=sk-abc123

# Multiple keys written under a group comment
cb env add database --secret DB_HOST=localhost --secret DB_PORT=5432

# Custom .env path
cb env add API_KEY --secret API_KEY=sk-abc123 --path config/.env

# Interactive (prompted when --secret is omitted)
cb env add API_KEY -p config/.env
```

### File output

After `cb env add database --secret DB_HOST=localhost --secret DB_PORT=5432`, the `.env` file contains:

```
# database
DB_HOST=localhost
DB_PORT=5432
```

### Interactive prompt

When `--secret` is omitted the CLI prompts for key-value pairs:

```
Enter secrets interactively. Leave KEY blank to finish.
  Key   : DB_HOST
  Value : localhost
  Key   : DB_PORT
  Value : 5432
  Key   :
✓  Secret database added to .env.
```

Note: `.env` values are displayed as you type (not masked), as they are typically non-sensitive configuration values.

!!! info "Key already exists"
    `add` raises `EnvFileKeyExistsError` if any supplied key already exists in the file. Use `update` to change an existing value.

---

## get

Retrieve a key's value from the `.env` file.

### Syntax

```
cb env get NAME [--output FORMAT] [--path PATH]
```

### Flags

| Flag | Short | Default | Description |
|---|---|---|---|
| `NAME` | — | — | Env var key name |
| `--output FORMAT` | `-o` | `rich` | Output format: `rich` or `json` |
| `--path PATH` | `-p` | `.env` | Path to the .env file |

### Examples

```bash
# Rich output (default)
cb env get DB_HOST

# Custom .env path
cb env get DB_HOST --path config/.env

# JSON output
cb env get DB_HOST -o json                         # {"DB_HOST": "localhost"}

# Extract value with jq
cb env get DB_HOST -o json | jq -r '.DB_HOST'     # localhost
```

### Error scenarios

| Situation | Message | Resolution |
|---|---|---|
| Key not found | `CredentialBridgeError` | Verify key name with `cb env list` |
| File not found | `CredentialBridgeError` | Check `--path` or create the file with `cb env add` |

---

## update

Update the value of an existing key. Only the specified keys change; all other keys in the file are preserved.

### Syntax

```
cb env update NAME [--secret KEY=VALUE]... [--path PATH]
```

### Flags

| Flag | Short | Required | Description |
|---|---|---|---|
| `NAME` | — | Yes | Env var key name |
| `--secret KEY=VALUE` | `-s` | Yes (or interactive) | New key-value pair (repeatable) |
| `--path PATH` | `-p` | No | Path to the .env file (default: `.env`) |

### Examples

```bash
# Update a single key
cb env update DB_HOST --secret DB_HOST=prod.db.example.com

# Update with a custom .env path
cb env update DB_HOST --path config/.env --secret DB_HOST=new-host

# Update multiple keys at once
cb env update database --secret DB_HOST=prod.db.example.com --secret DB_PORT=5433

# Interactive (prompted when --secret is omitted)
cb env update DB_HOST
```

### Error scenarios

| Situation | Message | Resolution |
|---|---|---|
| Key not found | `CredentialBridgeError` | Use `cb env add` to create it first |

---

## delete

Remove a key from the `.env` file.

### Syntax

```
cb env delete NAME [--yes] [--path PATH]
```

### Flags

| Flag | Short | Default | Description |
|---|---|---|---|
| `NAME` | — | — | Env var key name |
| `--yes` | `-y` | `False` | Skip confirmation prompt |
| `--path PATH` | `-p` | `.env` | Path to the .env file |

### Examples

```bash
# With confirmation prompt
cb env delete API_KEY

# Skip confirmation (CI/scripting)
cb env delete API_KEY --yes

# Custom .env path
cb env delete API_KEY --path config/.env --yes

# Short flag
cb env delete API_KEY -y
```

### Error scenarios

| Situation | Message | Resolution |
|---|---|---|
| Key not found | `CredentialBridgeError` | Verify key name with `cb env list` |

---

## list

List all keys defined in the `.env` file.

### Syntax

```
cb env list [--output FORMAT] [--path PATH]
```

### Flags

| Flag | Short | Default | Description |
|---|---|---|---|
| `--output FORMAT` | `-o` | `rich` | Output format: `rich` or `json` |
| `--path PATH` | `-p` | `.env` | Path to the .env file |

### Examples

```bash
# Rich table (default)
cb env list

# Custom .env path
cb env list --path config/.env

# JSON array of key names
cb env list -o json                    # ["DB_HOST", "DB_PORT", "API_KEY"]

# Print each key on its own line
cb env list -o json | python3 -c "import sys,json; [print(k) for k in json.load(sys.stdin)]"
```

---

## Scripting example

```bash
#!/bin/bash
# Populate .env from Vault for local development
export VAULT_ADDR=https://vault.example.com
export VAULT_TOKEN=s.dev-token

cb vault get myapp/database -o json | python3 -c "
import sys, json, subprocess
data = json.load(sys.stdin)
for k, v in data.items():
    subprocess.run(['cb', 'env', 'add', k, '--secret', f'{k}={v}'], check=True)
"
```
