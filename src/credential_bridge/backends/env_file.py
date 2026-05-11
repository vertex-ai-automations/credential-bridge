# src/credential_bridge/backends/env_file.py
import os
from io import StringIO
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
    if any(c in value for c in (' ', '\t', '\n', '\r', '#', '"', "'", '\\', '$', '`')):
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

    def _parse_lines(self, lines: List[str]) -> Dict[str, str]:
        """Parse dotenv key=value pairs from already-read lines (single file read)."""
        return dict(dotenv_values(stream=StringIO("".join(lines))))

    def _current_keys(self) -> Dict[str, str]:
        return self._parse_lines(self._read_lines()) if self.path.exists() else {}

    def _keys_for_group(self, group_name: str, lines: Optional[List[str]] = None) -> List[str]:
        """Return env-var keys that appear under a '# group_name' comment block."""
        if lines is None:
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
        lines = self._read_lines()
        keys = self._parse_lines(lines)
        if name in keys:
            return {name: keys[name]}
        group_keys = self._keys_for_group(name, lines=lines)
        if group_keys:
            return {k: keys[k] for k in group_keys if k in keys}
        raise EnvFileNotFoundError(f"Key or group '{name}' not found in {self.path}.")

    def update_secret(self, name: str, secret: Dict[str, Any]) -> None:
        existing = self._current_keys()
        missing = [k for k in secret if k not in existing]
        if missing:
            raise EnvFileNotFoundError(
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
        lines = self._read_lines()
        existing = self._parse_lines(lines)

        # Case 1: name is a direct key
        if name in existing:
            key_idx = next(
                (i for i, line in enumerate(lines)
                 if "=" in line
                 and not line.strip().startswith("#")
                 and line.split("=", 1)[0].strip() == name),
                None,
            )
            to_remove: set = set()
            if key_idx is not None:
                to_remove.add(key_idx)
                # Walk backwards (skipping blank lines) to find a preceding group-header comment
                comment_idx = None
                for i in range(key_idx - 1, -1, -1):
                    s = lines[i].strip()
                    if not s:
                        continue
                    if s.startswith("#"):
                        comment_idx = i
                    break
                if comment_idx is not None:
                    # Remove the comment header only if no other key=value lines follow it
                    has_sibling_keys = False
                    for i in range(comment_idx + 1, len(lines)):
                        s = lines[i].strip()
                        if s.startswith("#"):
                            break
                        if "=" in s and not s.startswith("#") and i != key_idx:
                            has_sibling_keys = True
                            break
                    if not has_sibling_keys:
                        to_remove.add(comment_idx)
            new_lines = [line for i, line in enumerate(lines) if i not in to_remove]
            self._write_lines(new_lines)
            if self.load_into_environ:
                os.environ.pop(name, None)
            return

        # Case 2: name is a group label — delete the header comment and all its keys
        group_keys = self._keys_for_group(name, lines=lines)
        if group_keys:
            to_remove = set()
            for i, line in enumerate(lines):
                if line.strip() == f"# {name}":
                    to_remove.add(i)
                    j = i + 1
                    while j < len(lines):
                        if lines[j].strip().startswith("#"):
                            break
                        to_remove.add(j)
                        j += 1
                    break
            new_lines = [line for i, line in enumerate(lines) if i not in to_remove]
            self._write_lines(new_lines)
            if self.load_into_environ:
                for k in group_keys:
                    os.environ.pop(k, None)
            return

        raise EnvFileNotFoundError(f"Key or group '{name}' not found in {self.path}.")

    def list_secrets(self, path: str = "") -> List[str]:
        return list(self._current_keys().keys())
