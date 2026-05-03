"""Tests for BaseSecretBackend abstract base class."""

import pytest
from credential_bridge.backends.base import BaseSecretBackend


def test_cannot_instantiate_without_all_methods():
    """Should raise TypeError when abstract methods are not implemented."""
    class Incomplete(BaseSecretBackend):
        pass  # missing all abstract methods

    with pytest.raises(TypeError):
        Incomplete()


def test_can_instantiate_complete_subclass():
    """Should instantiate when all abstract methods are implemented."""
    class Complete(BaseSecretBackend):
        backend_name = "test"

        def add_secret(self, name, secret): pass
        def get_secret(self, name): return {}
        def update_secret(self, name, secret): pass
        def delete_secret(self, name): pass
        def list_secrets(self, path=""): return []

    backend = Complete()
    assert backend.backend_name == "test"


def test_partial_subclass_raises_type_error():
    """Should raise TypeError when only some abstract methods are implemented."""
    class Partial(BaseSecretBackend):
        def add_secret(self, name, secret): pass
        # missing 4 methods

    with pytest.raises(TypeError):
        Partial()


def test_backend_name_enforced_on_concrete_subclass():
    """Concrete subclass without backend_name should raise TypeError at class definition."""
    with pytest.raises(TypeError, match="backend_name"):
        class Complete(BaseSecretBackend):
            def add_secret(self, name, secret): pass
            def get_secret(self, name): return {}
            def update_secret(self, name, secret): pass
            def delete_secret(self, name): pass
            def list_secrets(self, path=""): return []
