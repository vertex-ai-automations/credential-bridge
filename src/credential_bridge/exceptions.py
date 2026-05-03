"""Exception hierarchy for credential-bridge."""


class CredentialBridgeError(Exception):
    """Base exception for all credential-bridge errors."""


class BackendError(CredentialBridgeError):
    """Base exception for backend-specific errors."""


class VaultError(BackendError):
    """General HashiCorp Vault error."""


class VaultAuthError(VaultError):
    """Invalid token or AppRole credentials."""


class VaultConnectionError(VaultError):
    """Cannot reach Vault — bad URL or network issue."""


class KeyringError(BackendError):
    """System keyring error."""


class EnvFileError(BackendError):
    """Error reading or writing a .env file."""


class EnvFileNotFoundError(EnvFileError):
    """A requested key does not exist in the .env file."""


class EnvFileKeyExistsError(EnvFileError):
    """A key being added already exists in the .env file."""


class BackendNotRegisteredError(CredentialBridgeError):
    """Backend name not found in SecretsManager registry."""


class ConfigurationError(CredentialBridgeError):
    """Required configuration is missing or invalid."""
