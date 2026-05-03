# tests/unit/test_prompt_wizard.py
"""Tests for prompt_wizard — covers the pure logic functions, not interactive prompts."""
import pytest
from unittest.mock import MagicMock, patch


def test_is_vault_cred_valid_returns_false_without_vault_addr(monkeypatch):
    monkeypatch.delenv("VAULT_ADDR", raising=False)
    from credential_bridge.prompt_wizard import is_vault_cred_valid
    assert is_vault_cred_valid(vault_token="s.test") is False


def test_is_vault_cred_valid_returns_false_without_credentials(monkeypatch):
    monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com")
    from credential_bridge.prompt_wizard import is_vault_cred_valid
    assert is_vault_cred_valid() is False


def test_is_vault_cred_valid_returns_true_on_successful_auth(monkeypatch, mocker):
    monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com")
    mocker.patch("credential_bridge.manager.SecretsManager")
    from credential_bridge.prompt_wizard import is_vault_cred_valid
    assert is_vault_cred_valid(vault_token="s.valid") is True


def test_is_vault_cred_valid_returns_false_on_auth_error(monkeypatch, mocker):
    monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com")
    from credential_bridge.exceptions import VaultAuthError
    mocker.patch(
        "credential_bridge.manager.SecretsManager",
        side_effect=VaultAuthError("bad token"),
    )
    from credential_bridge.prompt_wizard import is_vault_cred_valid
    assert is_vault_cred_valid(vault_token="s.bad") is False


def test_run_keyring_cli_add(mocker):
    mock_manager = MagicMock()
    mock_cls = mocker.patch("credential_bridge.manager.SecretsManager", return_value=mock_manager)
    from credential_bridge.prompt_wizard import run_keyring_cli
    run_keyring_cli("add", "svc", "mykey", "myvalue")
    mock_manager.add_secret.assert_called_once_with("mykey", {"mykey": "myvalue"})


def test_run_keyring_cli_get(mocker, capsys):
    mock_manager = MagicMock()
    mock_manager.get_secret.return_value = {"mykey": "myvalue"}
    mocker.patch("credential_bridge.manager.SecretsManager", return_value=mock_manager)
    from credential_bridge.prompt_wizard import run_keyring_cli
    run_keyring_cli("get", "svc", "mykey", None)
    mock_manager.get_secret.assert_called_once_with("mykey")


def test_run_vault_cli_add(mocker):
    mock_manager = MagicMock()
    mocker.patch("credential_bridge.manager.SecretsManager", return_value=mock_manager)
    from credential_bridge.prompt_wizard import run_vault_cli
    run_vault_cli("add", "svc", "myapp/db", {"user": "admin"})
    mock_manager.add_secret.assert_called_once_with("myapp/db", {"user": "admin"})


def test_run_vault_cli_get(mocker):
    mock_manager = MagicMock()
    mock_manager.get_secret.return_value = {"user": "admin"}
    mocker.patch("credential_bridge.manager.SecretsManager", return_value=mock_manager)
    from credential_bridge.prompt_wizard import run_vault_cli
    run_vault_cli("get", "svc", "myapp/db", {})
    mock_manager.get_secret.assert_called_once_with("myapp/db")


def test_run_vault_cli_uses_secret_path_not_service_name(mocker):
    """Regression test: CRUD operations use secret_path, not service_name."""
    mock_manager = MagicMock()
    mocker.patch("credential_bridge.manager.SecretsManager", return_value=mock_manager)
    from credential_bridge.prompt_wizard import run_vault_cli
    run_vault_cli("delete", "my-service-tag", "actual/secret/path", {})
    mock_manager.delete_secret.assert_called_once_with("actual/secret/path")
    # service_name should NOT be used as the path
    for call in mock_manager.delete_secret.call_args_list:
        assert "my-service-tag" not in str(call)
