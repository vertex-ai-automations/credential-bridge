import pytest
from credential_bridge.exceptions import (
    CredentialBridgeError, BackendError,
    VaultError, VaultAuthError, VaultConnectionError,
    KeyringError, EnvFileError, EnvFileNotFoundError,
    BackendNotRegisteredError, ConfigurationError,
)


def test_vault_auth_error_is_vault_error():
    assert issubclass(VaultAuthError, VaultError)

def test_vault_error_is_backend_error():
    assert issubclass(VaultError, BackendError)

def test_backend_error_is_credential_bridge_error():
    assert issubclass(BackendError, CredentialBridgeError)

def test_env_file_not_found_is_env_file_error():
    assert issubclass(EnvFileNotFoundError, EnvFileError)

def test_backend_not_registered_is_credential_bridge_error():
    assert issubclass(BackendNotRegisteredError, CredentialBridgeError)

def test_configuration_error_is_credential_bridge_error():
    assert issubclass(ConfigurationError, CredentialBridgeError)

def test_exceptions_are_catchable_as_base():
    with pytest.raises(CredentialBridgeError):
        raise VaultAuthError("bad token")

def test_keyring_error_is_backend_error():
    assert issubclass(KeyringError, BackendError)

def test_vault_connection_error_is_vault_error():
    assert issubclass(VaultConnectionError, VaultError)

def test_env_file_error_is_backend_error():
    assert issubclass(EnvFileError, BackendError)

def test_env_file_key_exists_error_is_env_file_error():
    from credential_bridge.exceptions import EnvFileKeyExistsError, EnvFileError
    assert issubclass(EnvFileKeyExistsError, EnvFileError)

def test_vault_secret_not_found_is_vault_error():
    from credential_bridge.exceptions import VaultSecretNotFoundError, VaultError
    assert issubclass(VaultSecretNotFoundError, VaultError)
