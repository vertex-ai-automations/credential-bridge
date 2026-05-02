# src/credential_bridge/backends/env_file.py
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from dotenv import dotenv_values

from ..exceptions import EnvFileError, EnvFileNotFoundError
from .base import BaseSecretBackend


class EnvFileBackend(BaseSecretBackend):
    """.env file secrets backend with full CRUD and atomic writes."""

    backend_name = "env"

    def __init__(
        self,
        path: Union[str, Path] = ".env",
        load_into_environ: bool = False,
        encoding: str = "utf-8",
    ) -> None:
        self.path = Path(path)
        self.load_into_environ = load_into_environ
        self.encoding = encoding

    def _read_lines(self) -> List[str]:
        if not self.path.exists():
            return []
        return self.path.read_text(encoding=self.encoding).splitlines(keepends=True)

    def _write_lines(self, lines: List[str]) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text("".join(lines), encoding=self.encoding)
        os.replace(tmp, self.path)

    def _current_keys(self) -> Dict[str, str]:
        return dict(dotenv_values(self.path)) if self.path.exists() else {}

    def _sync_environ(self, keys: Dict[str, str]) -> None:
        for k, v in keys.items():
            os.environ[k] = str(v)

    def add_secret(self, name: str, secret: Dict[str, Any]) -> None:
        existing = self._current_keys()
        conflicts = [k for k in secret if k in existing]
        if conflicts:
            raise EnvFileError(
                f"Key(s) already exist in {self.path}: {conflicts}. "
                "Use update_secret() to change them."
            )
        lines = self._read_lines()
        lines.append(f"\n# {name}\n")
        for k, v in secret.items():
            lines.append(f"{k}={v}\n")
        self._write_lines(lines)
        if self.load_into_environ:
            self._sync_environ({k: str(v) for k, v in secret.items()})

    def get_secret(self, name: str) -> Dict[str, Any]:
        keys = self._current_keys()
        if name not in keys:
            raise EnvFileNotFoundError(f"Key '{name}' not found in {self.path}.")
        return {name: keys[name]}

    def update_secret(self, name: str, secret: Dict[str, Any]) -> None:
        existing = self._current_keys()
        found = {k for k in secret if k in existing}
        if not found:
            raise EnvFileError(
                f"None of the specified keys {list(secret)} not found in {self.path}. "
                "Use add_secret() first."
            )
        lines = self._read_lines()
        updated: Dict[str, str] = {}
        new_lines = []
        for line in lines:
            if "=" in line and not line.strip().startswith("#"):
                key = line.split("=", 1)[0].strip()
                if key in secret:
                    new_lines.append(f"{key}={secret[key]}\n")
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
        new_lines = []
        skip_next_comment = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Check if this comment precedes only the key we're deleting
            if stripped.startswith("#") and not skip_next_comment:
                # Look ahead: find next non-empty line
                remaining = [l for l in lines[i + 1:] if l.strip()]
                if remaining:
                    next_key = remaining[0].split("=", 1)[0].strip() if "=" in remaining[0] else None
                    if next_key == name:
                        # Check if there's another key after the deleted one under same comment
                        after = [l for l in lines[i + 1:] if l.strip() and not l.strip().startswith("#")]
                        if len(after) == 1:
                            skip_next_comment = True
                            continue
            if skip_next_comment and stripped == "":
                continue
            if "=" in line and not stripped.startswith("#"):
                key = line.split("=", 1)[0].strip()
                if key == name:
                    skip_next_comment = False
                    continue
            new_lines.append(line)
        self._write_lines(new_lines)
        if self.load_into_environ:
            os.environ.pop(name, None)

    def list_secrets(self, path: str = "") -> List[str]:
        return list(self._current_keys().keys())
