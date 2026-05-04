# src/credential_bridge/backends/env_file.py
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from dotenv import dotenv_values

from ..exceptions import EnvFileError, EnvFileKeyExistsError, EnvFileNotFoundError
from .base import BaseSecretBackend


def _quote_value(value: str) -> str:
    """Quote a .env value if it contains spaces or special characters."""
    # Already properly quoted — same quote char opens and closes with no unescaped inner match
    if len(value) >= 2:
        for q in ('"', "'"):
            if value[0] == q and value[-1] == q:
                inner = value[1:-1]
                if q not in inner:
                    return value
                break
    # Needs quoting if contains spaces or special chars
    if any(c in value for c in (' ', '\t', '#', '"', "'", '\\', '$', '`')):
        escaped = value.replace('\\', '\\\\').replace('"', '\\"')
        return f'"{escaped}"'
    return value


class EnvFileBackend(BaseSecretBackend):
    """.env file secrets backend with full CRUD and atomic writes."""

    backend_name = "env"

    def __init__(
        self,
        path: Union[str, Path] = ".env",
        load_into_environ: bool = False,
        encoding: str = "utf-8",
    ) -> None:
        self.path = Path(path).resolve()
        self.load_into_environ = load_into_environ
        self.encoding = encoding

    def _read_lines(self) -> List[str]:
        if not self.path.exists():
            return []
        return self.path.read_text(encoding=self.encoding).splitlines(keepends=True)

    def _write_lines(self, lines: List[str]) -> None:
        tmp = self.path.parent / (self.path.name + ".tmp")
        try:
            tmp.write_text("".join(lines), encoding=self.encoding)
            os.replace(str(tmp), str(self.path))
        except Exception as exc:
            tmp.unlink(missing_ok=True)
            raise EnvFileError(f"Failed to write {self.path}: {exc}") from exc

    def _current_keys(self) -> Dict[str, str]:
        return dict(dotenv_values(self.path)) if self.path.exists() else {}

    def _keys_for_group(self, group_name: str) -> List[str]:
        """Return env-var keys that appear under a '# group_name' comment block."""
        lines = self._read_lines()
        in_group = False
        result = []
        for line in lines:
            stripped = line.strip()
            if stripped == f"# {group_name}":
                in_group = True
                continue
            if in_group:
                if stripped.startswith("#"):
                    break
                if "=" in stripped:
                    result.append(stripped.split("=", 1)[0].strip())
        return result

    def _sync_environ(self, keys: Dict[str, str]) -> None:
        for k, v in keys.items():
            os.environ[k] = str(v)

    def add_secret(self, name: str, secret: Dict[str, Any]) -> None:
        existing = self._current_keys()
        conflicts = [k for k in secret if k in existing]
        if conflicts:
            raise EnvFileKeyExistsError(
                f"Key(s) already exist in {self.path}: {conflicts}. "
                "Use update_secret() to change them."
            )
        lines = self._read_lines()
        lines.append(f"\n# {name}\n")
        for k, v in secret.items():
            lines.append(f"{k}={_quote_value(str(v))}\n")
        self._write_lines(lines)
        if self.load_into_environ:
            self._sync_environ({k: str(v) for k, v in secret.items()})

    def get_secret(self, name: str) -> Dict[str, Any]:
        keys = self._current_keys()
        if name in keys:
            return {name: keys[name]}
        group_keys = self._keys_for_group(name)
        if group_keys:
            return {k: keys[k] for k in group_keys if k in keys}
        raise EnvFileNotFoundError(f"Key or group '{name}' not found in {self.path}.")

    def update_secret(self, name: str, secret: Dict[str, Any]) -> None:
        existing = self._current_keys()
        missing = [k for k in secret if k not in existing]
        if missing:
            raise EnvFileError(
                f"Key(s) {missing} not found in {self.path}. Use add_secret() first."
            )
        lines = self._read_lines()
        updated: Dict[str, str] = {}
        new_lines = []
        for line in lines:
            if "=" in line and not line.strip().startswith("#"):
                key = line.split("=", 1)[0].strip()
                if key in secret:
                    new_lines.append(f"{key}={_quote_value(str(secret[key]))}\n")
                    updated[key] = str(secret[key])
                    continue
            new_lines.append(line)
        self._write_lines(new_lines)
        if self.load_into_environ:
            self._sync_environ(updated)

    def delete_secret(self, name: str) -> None:
        existing = self._current_keys()
        if name not in existing:
            raise EnvFileNotFoundError(f"Key '{name}' not found in {self.path}.")
        lines = self._read_lines()
        new_lines = [
            line for line in lines
            if not ("=" in line and not line.strip().startswith("#") and line.split("=", 1)[0].strip() == name)
        ]
        self._write_lines(new_lines)
        if self.load_into_environ:
            os.environ.pop(name, None)

    def list_secrets(self, path: str = "") -> List[str]:
        return list(self._current_keys().keys())
