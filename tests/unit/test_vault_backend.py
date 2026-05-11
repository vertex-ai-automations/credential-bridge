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
    # Return a high TTL so _refresh_token_if_needed skips renewal
    client.auth.token.lookup_self.return_value = {"data": {"ttl": 3600}}
    mocker.patch("credential_bridge.backends.vault.hvac.Client", return_value=client)
    mocker.patch("credential_bridge.backends.vault.load_config", return_value={})
    mocker.patch("credential_bridge.backends.vault.save_config")
    return client


def test_raises_configuration_error_without_vault_url(mocker):
    mocker.patch("credential_bridge.backends.vault.os.environ.get", return_value=None)
    mocker.patch("credential_bridge.backends.vault.load_config", return_value={})
    mocker.patch("credential_bridge.backends.vault.save_config")
    # ConfigurationError must fire before getpass.getuser() or session setup
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
    import getpass
    backend = VaultBackend(vault_url="https://vault.example.com", vault_token="s.test")
    assert backend.mount_point == getpass.getuser()


def test_list_secrets_empty_path(mock_hvac):
    import getpass
    mock_hvac.secrets.kv.v2.list_secrets.return_value = {"data": {"keys": ["a", "b"]}}
    backend = VaultBackend(vault_url="https://vault.example.com", vault_token="s.test")
    result = backend.list_secrets()
    mock_hvac.secrets.kv.v2.list_secrets.assert_called_once_with(path="", mount_point=getpass.getuser())


# ---------------------------------------------------------------------------
# 2a: AppRole authentication
# ---------------------------------------------------------------------------

def test_approle_authentication_success(mocker):
    """AppRole auth path — different from token path."""
    client = MagicMock()
    client.is_authenticated.return_value = True
    client.auth.approle.login.return_value = {
        "auth": {"client_token": "s.approle-token"}
    }
    client.auth.token.lookup_self.return_value = {"data": {"ttl": 3600}}
    mocker.patch("credential_bridge.backends.vault.hvac.Client", return_value=client)
    mocker.patch("credential_bridge.backends.vault.load_config", return_value={})
    mocker.patch("credential_bridge.backends.vault.save_config")

    backend = VaultBackend(
        vault_url="https://vault.example.com",
        vault_role_id="my-role-id",
        vault_secret_id="my-secret-id",
    )
    assert backend.client.token == "s.approle-token"
    client.auth.approle.login.assert_called_once_with(
        role_id="my-role-id", secret_id="my-secret-id"
    )


def test_approle_auth_error_on_bad_credentials(mocker):
    """AppRole returns no auth token → VaultAuthError."""
    client = MagicMock()
    client.auth.approle.login.return_value = {}   # no "auth" key
    mocker.patch("credential_bridge.backends.vault.hvac.Client", return_value=client)
    mocker.patch("credential_bridge.backends.vault.load_config", return_value={})
    mocker.patch("credential_bridge.backends.vault.save_config")

    with pytest.raises(VaultAuthError):
        VaultBackend(
            vault_url="https://vault.example.com",
            vault_role_id="bad-role",
            vault_secret_id="bad-secret",
        )


# ---------------------------------------------------------------------------
# 2b: update_secret
# ---------------------------------------------------------------------------

def test_update_secret(mock_hvac):
    import getpass
    backend = VaultBackend(vault_url="https://vault.example.com", vault_token="s.test")
    backend.update_secret("myapp/db", {"pass": "newpass"})
    mock_hvac.secrets.kv.v2.patch.assert_called_once_with(
        path="myapp/db",
        secret={"pass": "newpass"},
        mount_point=getpass.getuser(),
    )


# ---------------------------------------------------------------------------
# 2c: token refresh
# ---------------------------------------------------------------------------

def test_refresh_token_renews_when_ttl_low(mock_hvac):
    """Token with TTL < 300 should be renewed."""
    mock_hvac.auth.token.lookup_self.return_value = {"data": {"ttl": 100}}
    backend = VaultBackend(vault_url="https://vault.example.com", vault_token="s.test")
    backend._refresh_token_if_needed()
    mock_hvac.auth.token.renew_self.assert_called_once_with()


def test_refresh_token_skips_when_ttl_ok(mock_hvac):
    """Token with TTL >= 300 should not be renewed."""
    mock_hvac.auth.token.lookup_self.return_value = {"data": {"ttl": 3600}}
    backend = VaultBackend(vault_url="https://vault.example.com", vault_token="s.test")
    backend._refresh_token_if_needed()
    mock_hvac.auth.token.renew_self.assert_not_called()


def test_refresh_token_swallows_exception(mock_hvac):
    """Failed token lookup should log a warning, not raise."""
    mock_hvac.auth.token.lookup_self.side_effect = Exception("lookup failed")
    backend = VaultBackend(vault_url="https://vault.example.com", vault_token="s.test")
    # Should not raise
    backend._refresh_token_if_needed()


# ---------------------------------------------------------------------------
# 2d: persist parameter
# ---------------------------------------------------------------------------

def test_credentials_not_persisted_by_default(mocker):
    """With persist=False (default), save_config should not be called."""
    client = MagicMock()
    client.is_authenticated.return_value = True
    mocker.patch("credential_bridge.backends.vault.hvac.Client", return_value=client)
    mocker.patch("credential_bridge.backends.vault.load_config", return_value={})
    mock_save = mocker.patch("credential_bridge.backends.vault.save_config")

    VaultBackend(vault_url="https://vault.example.com", vault_token="s.test")
    mock_save.assert_not_called()


def test_credentials_persisted_when_persist_true(mocker):
    """With persist=True, save_config should be called once."""
    client = MagicMock()
    client.is_authenticated.return_value = True
    mocker.patch("credential_bridge.backends.vault.hvac.Client", return_value=client)
    mocker.patch("credential_bridge.backends.vault.load_config", return_value={})
    mock_save = mocker.patch("credential_bridge.backends.vault.save_config")

    VaultBackend(vault_url="https://vault.example.com", vault_token="s.test", persist=True)
    mock_save.assert_called_once()


# ---------------------------------------------------------------------------
# 2e: VaultSecretNotFoundError
# ---------------------------------------------------------------------------

def test_get_secret_raises_vault_secret_not_found(mock_hvac):
    """InvalidPath from hvac should raise VaultSecretNotFoundError."""
    import hvac.exceptions
    from credential_bridge.exceptions import VaultSecretNotFoundError
    mock_hvac.secrets.kv.v2.read_secret.side_effect = hvac.exceptions.InvalidPath("secret/myapp/missing")
    backend = VaultBackend(vault_url="https://vault.example.com", vault_token="s.test")
    with pytest.raises(VaultSecretNotFoundError, match="does not exist"):
        backend.get_secret("myapp/missing")


def test_delete_secret_raises_vault_secret_not_found(mock_hvac):
    """InvalidPath from hvac on delete should raise VaultSecretNotFoundError."""
    import hvac.exceptions
    from credential_bridge.exceptions import VaultSecretNotFoundError
    mock_hvac.secrets.kv.v2.delete_metadata_and_all_versions.side_effect = hvac.exceptions.InvalidPath()
    backend = VaultBackend(vault_url="https://vault.example.com", vault_token="s.test")
    with pytest.raises(VaultSecretNotFoundError):
        backend.delete_secret("myapp/missing")


# ---------------------------------------------------------------------------
# 2f: connection errors surfaced from CRUD methods
# ---------------------------------------------------------------------------

def test_add_secret_raises_vault_connection_error_on_network_failure(mock_hvac):
    import requests as _requests
    from credential_bridge.exceptions import VaultConnectionError
    mock_hvac.secrets.kv.v2.create_or_update_secret.side_effect = _requests.ConnectionError("unreachable")
    backend = VaultBackend(vault_url="https://vault.example.com", vault_token="s.test")
    with pytest.raises(VaultConnectionError):
        backend.add_secret("myapp/db", {"k": "v"})


def test_get_secret_raises_vault_connection_error_on_timeout(mock_hvac):
    import requests as _requests
    from credential_bridge.exceptions import VaultConnectionError
    mock_hvac.secrets.kv.v2.read_secret.side_effect = _requests.Timeout("timed out")
    backend = VaultBackend(vault_url="https://vault.example.com", vault_token="s.test")
    with pytest.raises(VaultConnectionError):
        backend.get_secret("myapp/db")


# ---------------------------------------------------------------------------
# 2g: version-management helpers
# ---------------------------------------------------------------------------

def test_read_secret_metadata(mock_hvac):
    mock_hvac.secrets.kv.v2.read_secret_metadata.return_value = {"data": {"versions": {}}}
    backend = VaultBackend(vault_url="https://vault.example.com", vault_token="s.test")
    result = backend.read_secret_metadata("myapp/db")
    mock_hvac.secrets.kv.v2.read_secret_metadata.assert_called_once_with(
        path="myapp/db", mount_point=backend.mount_point
    )
    assert result == {"data": {"versions": {}}}


def test_delete_secret_versions(mock_hvac):
    backend = VaultBackend(vault_url="https://vault.example.com", vault_token="s.test")
    backend.delete_secret_versions("myapp/db", [1, 2])
    mock_hvac.secrets.kv.v2.delete_secret_versions.assert_called_once_with(
        path="myapp/db", versions=[1, 2], mount_point=backend.mount_point
    )


def test_undelete_secret_versions(mock_hvac):
    backend = VaultBackend(vault_url="https://vault.example.com", vault_token="s.test")
    backend.undelete_secret_versions("myapp/db", [1])
    mock_hvac.secrets.kv.v2.undelete_secret_versions.assert_called_once_with(
        path="myapp/db", versions=[1], mount_point=backend.mount_point
    )


def test_destroy_secret_versions(mock_hvac):
    backend = VaultBackend(vault_url="https://vault.example.com", vault_token="s.test")
    backend.destroy_secret_versions("myapp/db", [1, 2, 3])
    mock_hvac.secrets.kv.v2.destroy_secret_versions.assert_called_once_with(
        path="myapp/db", versions=[1, 2, 3], mount_point=backend.mount_point
    )


def test_get_config(mock_hvac):
    mock_hvac.secrets.kv.v2.read_configuration.return_value = {"data": {"max_versions": 10}}
    backend = VaultBackend(vault_url="https://vault.example.com", vault_token="s.test")
    result = backend.get_config()
    mock_hvac.secrets.kv.v2.read_configuration.assert_called_once_with(mount_point=backend.mount_point)
    assert result == {"data": {"max_versions": 10}}
