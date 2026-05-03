import json
from pathlib import Path
import pytest
import credential_bridge.utils as u


def test_config_file_uses_home_directory():
    assert u.CONFIG_FILE == Path.home() / ".vault_config.json"


def test_load_config_returns_empty_dict_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(u, "CONFIG_FILE", tmp_path / "missing.json")
    assert u.load_config() == {}


def test_save_and_load_config_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(u, "CONFIG_FILE", tmp_path / ".vault_config.json")
    data = {"vault_token": "s.test"}
    u.save_config(data)
    assert u.load_config() == data


def test_get_session_returns_requests_session():
    import requests
    session = u.get_session()
    assert isinstance(session, requests.Session)
    assert session.verify is True


def test_get_session_with_cert():
    session = u.get_session(cert="/path/to/cert.pem")
    assert session.verify == "/path/to/cert.pem"


def test_no_vault_addr_enum_in_utils():
    assert not hasattr(u, "VaultAddr")


def test_no_get_vault_addr_in_utils():
    assert not hasattr(u, "get_vault_addr")


def test_get_vault_credentials_returns_tuple(tmp_path, monkeypatch):
    monkeypatch.setattr(u, "CONFIG_FILE", tmp_path / ".vault_config.json")
    u.save_config({"vault_token": "s.test", "vault_role_id": None, "vault_secret_id": None})
    token, role_id, secret_id = u.get_vault_credentials()
    assert token == "s.test"
    assert role_id is None
