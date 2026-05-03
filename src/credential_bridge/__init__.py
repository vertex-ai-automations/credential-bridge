# src/credential_bridge/__init__.py
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("credential-bridge")
except PackageNotFoundError:
    __version__ = "unknown"
from .backends import BaseSecretBackend, EnvFileBackend, KeyringBackend, VaultBackend
from .exceptions import (
    BackendError,
    BackendNotRegisteredError,
    ConfigurationError,
    CredentialBridgeError,
    EnvFileError,
    EnvFileNotFoundError,
    KeyringError,
    VaultAuthError,
    VaultConnectionError,
    VaultError,
)
from .manager import SecretsManager

# Backwards-compatibility aliases
VaultManager = VaultBackend
KeyringManager = KeyringBackend

__all__ = [
    "__version__",
    "SecretsManager",
    "BaseSecretBackend",
    "VaultBackend",
    "KeyringBackend",
    "EnvFileBackend",
    "CredentialBridgeError",
    "BackendError",
    "VaultError",
    "VaultAuthError",
    "VaultConnectionError",
    "KeyringError",
    "EnvFileError",
    "EnvFileNotFoundError",
    "BackendNotRegisteredError",
    "ConfigurationError",
    "VaultManager",
    "KeyringManager",
]
