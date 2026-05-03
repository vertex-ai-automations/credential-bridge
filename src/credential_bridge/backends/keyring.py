"""System keyring backend for credential-bridge."""

import json
from typing import Any, Dict, List, Optional, Union

import keyring
from keyring.errors import KeyringError as _KeyringLibError
from pylogshield import LogLevel, PyLogShield, get_logger

from ..exceptions import ConfigurationError, KeyringError
from .base import BaseSecretBackend


class KeyringBackend(BaseSecretBackend):
    """System keyring backend. Stores dicts as JSON strings."""

    backend_name = "keyring"

    def __init__(
        self,
        service_name: str = "default_service",
        log_level: Union[LogLevel, str] = LogLevel.WARNING,
        logger: Optional[PyLogShield] = None,
        mask: bool = True,
    ) -> None:
        self.service_name = service_name
        self.mask = mask
        if logger and not isinstance(logger, PyLogShield):
            raise ConfigurationError("logger must be a PyLogShield instance.")
        self.logger = logger or get_logger(name="credential_bridge", log_level=log_level)

    def __repr__(self) -> str:
        return f"KeyringBackend(service_name={self.service_name!r})"

    def add_secret(self, name: str, secret: Dict[str, Any]) -> None:
        try:
            keyring.set_password(self.service_name, name, json.dumps(secret))
            self.logger.info(f"Keyring secret added: {name}", mask=self.mask)
        except _KeyringLibError as e:
            raise KeyringError(f"Failed to add '{name}': {e}") from e

    def get_secret(self, name: str) -> Dict[str, Any]:
        try:
            value = keyring.get_password(self.service_name, name)
            if value is None:
                raise KeyringError(
                    f"Secret '{name}' not found in keyring service '{self.service_name}'."
                )
            return json.loads(value)
        except KeyringError:
            raise
        except _KeyringLibError as e:
            raise KeyringError(f"Failed to get '{name}': {e}") from e

    def update_secret(self, name: str, secret: Dict[str, Any]) -> None:
        try:
            existing = keyring.get_password(self.service_name, name)
            if existing is None:
                raise KeyringError(
                    f"Secret '{name}' does not exist — use add_secret() first."
                )
            keyring.set_password(self.service_name, name, json.dumps(secret))
            self.logger.info(f"Keyring secret updated: {name}", mask=self.mask)
        except KeyringError:
            raise
        except _KeyringLibError as e:
            raise KeyringError(f"Failed to update '{name}': {e}") from e

    def delete_secret(self, name: str) -> None:
        try:
            existing = keyring.get_password(self.service_name, name)
            if existing is None:
                raise KeyringError(
                    f"Secret '{name}' not found in keyring service '{self.service_name}'."
                )
            keyring.delete_password(self.service_name, name)
            self.logger.info(f"Keyring secret deleted: {name}")
        except KeyringError:
            raise
        except _KeyringLibError as e:
            raise KeyringError(f"Failed to delete '{name}': {e}") from e

    def list_secrets(self, path: str = "") -> List[str]:
        raise NotImplementedError(
            "KeyringBackend.list_secrets() is not supported on this platform. "
            "Windows Credential Manager and macOS Keychain do not expose enumeration APIs."
        )
