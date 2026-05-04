# tests/unit/test_manager.py
import pytest
from credential_bridge.manager import SecretsManager
from credential_bridge.backends.base import BaseSecretBackend
from credential_bridge.exceptions import BackendNotRegisteredError


class FakeBackend(BaseSecretBackend):
    backend_name = "fake"
    def __init__(self, **kwargs): self.kwargs = kwargs
    def add_secret(self, name, secret): pass
    def get_secret(self, name): return {"key": "val"}
    def update_secret(self, name, secret): pass
    def delete_secret(self, name): pass
    def list_secrets(self, path=""): return ["a", "b"]


def test_register_and_use_custom_backend():
    SecretsManager.register_backend("fake", FakeBackend)
    sm = SecretsManager("fake")
    assert isinstance(sm.backend, FakeBackend)


def test_unknown_backend_raises():
    with pytest.raises(BackendNotRegisteredError, match="unknown_xyz"):
        SecretsManager("unknown_xyz")


def test_kwargs_forwarded_to_backend():
    SecretsManager.register_backend("fake", FakeBackend)
    sm = SecretsManager("fake", some_arg="hello")
    assert sm.backend.kwargs.get("some_arg") == "hello"


def test_get_secret_delegates():
    SecretsManager.register_backend("fake", FakeBackend)
    sm = SecretsManager("fake")
    assert sm.get_secret("x") == {"key": "val"}


def test_list_secrets_delegates():
    SecretsManager.register_backend("fake", FakeBackend)
    sm = SecretsManager("fake")
    assert sm.list_secrets() == ["a", "b"]


def test_builtin_backends_registered():
    assert "vault" in SecretsManager._registry
    assert "keyring" in SecretsManager._registry
    assert "env" in SecretsManager._registry


def test_backend_property_returns_instance():
    SecretsManager.register_backend("fake", FakeBackend)
    sm = SecretsManager("fake")
    assert sm.backend is sm._backend


def test_add_secret_delegates(mocker):
    SecretsManager.register_backend("fake", FakeBackend)
    sm = SecretsManager("fake")
    mock_add = mocker.patch.object(sm._backend, "add_secret")
    sm.add_secret("name", {"k": "v"})
    mock_add.assert_called_once_with("name", {"k": "v"})


def test_delete_secret_delegates(mocker):
    SecretsManager.register_backend("fake", FakeBackend)
    sm = SecretsManager("fake")
    mock_del = mocker.patch.object(sm._backend, "delete_secret")
    sm.delete_secret("name")
    mock_del.assert_called_once_with("name")
