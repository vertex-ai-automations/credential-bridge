# .env File Backend

## When to use

`EnvFileBackend` is the right choice when you follow the
[12-factor app](https://12factor.net/config) methodology and want to keep
configuration in a plain-text `.env` file that lives alongside your project.
It is ideal for local development and CI/CD pipelines where secrets are supplied
as environment-variable overrides, and for cases where you need a human-readable,
easily-diffed config file that is excluded from version control.

!!! danger "Never commit .env to git"
    Add `.env` to your `.gitignore` immediately. A committed `.env` file can
    expose credentials to anyone with access to the repository, including past
    contributors and CI logs.

    ```gitignore
    # .gitignore
    .env
    .env.*
    !.env.example
    ```

## Constructor parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `path` | `str \| Path` | `".env"` | Path to the `.env` file. Resolved to an absolute path at init time. |
| `load_into_environ` | `bool` | `False` | If `True`, sync written keys into `os.environ` on every mutating operation. |
| `encoding` | `str` | `"utf-8"` | File encoding used for reading and writing. |

### Path resolution

The `path` argument is resolved to an absolute path using `Path.resolve()` during
`__init__`. This means subsequent changes to the process working directory
(e.g. `os.chdir()`) do not affect which file the backend reads and writes.

```python
import os
from credential_bridge import EnvFileBackend

backend = EnvFileBackend(path=".env")
# backend.path is now an absolute Path, e.g. /home/user/project/.env

os.chdir("/tmp")  # Does NOT change which file backend uses
backend.list_secrets()  # Still reads /home/user/project/.env
```

## The `name` parameter

The `name` argument to `add_secret` and the operation methods has different
semantics depending on the operation:

- **`add_secret(name, secret)`** — `name` is written as a comment header
  (`# name`) above the new keys. It acts as a human-readable label for the
  group of keys being added. It is **not** itself stored as a key.
- **`get_secret(name)`** — `name` is the exact environment variable key to look
  up (e.g. `"DB_HOST"`).
- **`update_secret(name, secret)`** — `name` is passed for consistency with the
  base interface but the actual keys updated are the ones in the `secret` dict.
- **`delete_secret(name)`** — `name` is the exact environment variable key to
  remove.

## File format

After calling `add_secret("database", {"DB_HOST": "localhost", "DB_PORT": "5432"})`,
the `.env` file contains:

```dotenv
# database
DB_HOST=localhost
DB_PORT=5432
```

Multiple calls append additional groups:

```python
backend.add_secret("database", {"DB_HOST": "localhost", "DB_PORT": "5432"})
backend.add_secret("API_KEY", {"API_KEY": "sk-abc123"})
```

```dotenv
# database
DB_HOST=localhost
DB_PORT=5432

# API_KEY
API_KEY=sk-abc123
```

### Value quoting

Values that contain spaces, tabs, `#`, `"`, `'`, `\`, `$`, or `` ` `` are
automatically wrapped in double quotes. You do not need to quote values
yourself.

```python
backend.add_secret("GREETING", {"GREETING": "hello world"})
# writes: GREETING="hello world"

backend.add_secret("PATH_VAR", {"PATH_VAR": "/usr/local/bin"})
# writes: PATH_VAR=/usr/local/bin  (no quotes needed)
```

## CRUD operations

### add_secret

Appends a comment header and one or more `KEY=VALUE` lines to the file. Raises
`EnvFileKeyExistsError` if **any** of the keys in `secret` already exist in the
file — use `update_secret()` to change existing keys.

```python
from credential_bridge import EnvFileBackend

backend = EnvFileBackend(path=".env")

# Add a group of related keys
backend.add_secret("database", {"DB_HOST": "localhost", "DB_PORT": "5432"})

# Add a single key
backend.add_secret("API_KEY", {"API_KEY": "sk-abc123"})
```

CLI equivalent:

```bash
cb env add database --secret DB_HOST=localhost --secret DB_PORT=5432
cb env add API_KEY --secret API_KEY=sk-abc123
```

### get_secret

Returns a single-key dict for the given environment variable name. Raises
`EnvFileNotFoundError` if the key is not present in the file.

```python
result = backend.get_secret("DB_HOST")
# {"DB_HOST": "localhost"}

result = backend.get_secret("API_KEY")
# {"API_KEY": "sk-abc123"}
```

CLI equivalent:

```bash
cb env get DB_HOST
cb env get API_KEY --path config/.env
```

### update_secret

Performs a **partial update** — only the keys specified in `secret` are changed;
all other lines in the file are preserved exactly as they are. Raises
`EnvFileError` if **any** key in `secret` is missing from the file — use
`add_secret()` first. If the `.env` file does not exist, all specified keys are
considered missing and `EnvFileError` is raised.

```python
# Only DB_HOST is changed; DB_PORT and all other keys are untouched
backend.update_secret("DB_HOST", {"DB_HOST": "prod-db.example.com"})
```

CLI equivalent:

```bash
cb env update DB_HOST --secret DB_HOST=prod-db.example.com
```

### delete_secret

Removes the line for the specified key. The comment header for the group is
**not** automatically removed. Raises `EnvFileNotFoundError` if the key does
not exist.

```python
backend.delete_secret("API_KEY")
```

CLI equivalent:

```bash
cb env delete API_KEY --yes
```

### list_secrets

Returns a list of all environment variable keys currently defined in the file,
in the order they appear.

```python
keys = backend.list_secrets()
# ["DB_HOST", "DB_PORT", "API_KEY"]
```

CLI equivalent:

```bash
cb env list
cb env list --path config/.env
```

## Atomic writes

All write operations (`add_secret`, `update_secret`, `delete_secret`) use a
two-step atomic strategy to prevent file corruption if the process is interrupted
mid-write:

1. The new content is written to a temporary file with `.tmp` appended to the
   target filename (e.g. `secrets.env` → `secrets.env.tmp`) in the same directory
   as the target file.
2. `os.replace()` is called to atomically rename the temp file back to the original filename.

`os.replace()` is atomic on POSIX systems and atomic on NTFS on Windows (within
the same volume), so a concurrent reader never sees a partial write.

## Loading into `os.environ`

Set `load_into_environ=True` to have every mutating operation automatically sync
the affected keys into `os.environ`:

```python
import os
from credential_bridge import EnvFileBackend

backend = EnvFileBackend(path=".env", load_into_environ=True)

backend.add_secret("PORT", {"PORT": "8080"})
print(os.environ["PORT"])  # "8080"

backend.update_secret("PORT", {"PORT": "9090"})
print(os.environ["PORT"])  # "9090"

backend.delete_secret("PORT")
# os.environ["PORT"] is now unset
```

`get_secret()` and `list_secrets()` are read-only and never modify `os.environ`.

## Error handling

```python
from credential_bridge import (
    EnvFileError,
    EnvFileNotFoundError,
    EnvFileKeyExistsError,
)

try:
    backend.add_secret("DB_HOST", {"DB_HOST": "new-host"})
except EnvFileKeyExistsError:
    print("Key already exists — use update_secret() to change it")

try:
    backend.get_secret("MISSING_KEY")
except EnvFileNotFoundError:
    print("Key not found in .env file")

try:
    backend.update_secret("MISSING_KEY", {"MISSING_KEY": "value"})
except EnvFileError:
    print("One or more keys not found — use add_secret() first")
```

### Common errors

| Exception | Cause | Resolution |
|---|---|---|
| `EnvFileKeyExistsError` | `add_secret()` called when one or more keys already exist | Use `update_secret()` to change existing keys |
| `EnvFileNotFoundError` | `get_secret()` or `delete_secret()` called with a key not in the file | Check the key name with `list_secrets()` |
| `EnvFileError` | `update_secret()` called when one or more specified keys are missing | Use `add_secret()` to create them first |

`EnvFileNotFoundError` and `EnvFileKeyExistsError` are both subclasses of
`EnvFileError`, which is itself a subclass of `BackendError`.
