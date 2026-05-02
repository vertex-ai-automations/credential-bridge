# tests/unit/test_vault_backend.py
import pytest
from unittest.mock import MagicMock, patch
from credential_bridge.backends.vault import VaultBackend
from credential_bridge.exceptions import (
    ConfigurationError, VaultAuthError, VaultError
)


@pytest.fixture
def mock_hvac(mocker):
    client = MagicMock()
    client.is_authenticated.return_value = True
    mocker.patch("credential_bridge.backends.vault.hvac.Client", return_value=client)
    mocker.patch("credential_bridge.backends.vault.load_config", return_value={})
    mocker.patch("credential_bridge.backends.vault.save_config")
    return client


def test_raises_configuration_error_without_vault_url(mocker):
    mocker.patch("credential_bridge.backends.vault.os.environ.get", return_value=None)
    mocker.patch("credential_bridge.backends.vault.load_config", return_value={})
    mocker.patch("credential_bridge.backends.vault.save_config")
    with pytest.raises(ConfigurationError, match="VAULT_ADDR"):
        VaultBackend(vault_token="s.test")


def test_explicit_vault_url_used(mocker, mock_hvac):
    backend = VaultBackend(vault_url="https://vault.example.com", vault_token="s.test")
    assert backend.vault_addr == "https://vault.example.com"


def test_reads_vault_addr_from_env(mocker, mock_hvac):
    mocker.patch.dict("os.environ", {"VAULT_ADDR": "https://env.vault.com"})
    backend = VaultBackend(vault_token="s.test")
    assert backend.vault_addr == "https://env.vault.com"


def test_raises_when_both_token_and_approle(mocker):
    mocker.patch("credential_bridge.backends.vault.load_config", return_value={})
    mocker.patch("credential_bridge.backends.vault.save_config")
    with pytest.raises(ConfigurationError, match="not both"):
        VaultBackend(
            vault_url="https://vault.example.com",
            vault_token="s.test",
            vault_role_id="role",
            vault_secret_id="secret",
        )


def test_raises_when_no_credentials(mocker):
    mocker.patch("credential_bridge.backends.vault.load_config", return_value={})
    mocker.patch("credential_bridge.backends.vault.save_config")
    with pytest.raises(ConfigurationError, match="No authentication"):
        VaultBackend(vault_url="https://vault.example.com")


def test_vault_auth_error_on_bad_token(mocker):
    client = MagicMock()
    client.is_authenticated.return_value = False
    mocker.patch("credential_bridge.backends.vault.hvac.Client", return_value=client)
    mocker.patch("credential_bridge.backends.vault.load_config", return_value={})
    mocker.patch("credential_bridge.backends.vault.save_config")
    with pytest.raises(VaultAuthError):
        VaultBackend(vault_url="https://vault.example.com", vault_token="bad")


def test_add_secret(mock_hvac):
    backend = VaultBackend(vault_url="https://vault.example.com", vault_token="s.test")
    backend.add_secret("myapp/db", {"user": "admin", "pass": "secret"})
    mock_hvac.secrets.kv.v2.create_or_update_secret.assert_called_once()


def test_get_secret(mock_hvac):
    mock_hvac.secrets.kv.v2.read_secret.return_value = {
        "data": {"data": {"user": "admin"}}
    }
    backend = VaultBackend(vault_url="https://vault.example.com", vault_token="s.test")
    result = backend.get_secret("myapp/db")
    assert result == {"user": "admin"}


def test_delete_secret(mock_hvac):
    backend = VaultBackend(vault_url="https://vault.example.com", vault_token="s.test")
    backend.delete_secret("myapp/db")
    mock_hvac.secrets.kv.v2.delete_metadata_and_all_versions.assert_called_once()


def test_backend_name():
    assert VaultBackend.backend_name == "vault"


def test_mount_point_default(mock_hvac):
    backend = VaultBackend(vault_url="https://vault.example.com", vault_token="s.test")
    assert backend.mount_point == "secret"


def test_list_secrets_empty_path(mock_hvac):
    mock_hvac.secrets.kv.v2.list_secrets.return_value = {"data": {"keys": ["a", "b"]}}
    backend = VaultBackend(vault_url="https://vault.example.com", vault_token="s.test")
    result = backend.list_secrets()
    mock_hvac.secrets.kv.v2.list_secrets.assert_called_once_with(path="", mount_point="secret")
