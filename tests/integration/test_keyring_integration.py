# tests/integration/test_keyring_integration.py
import pytest

pytestmark = pytest.mark.integration

try:
    import keyring
    _backend = keyring.get_keyring()
    _has_real_keyring = "fail" not in type(_backend).__name__.lower()
except Exception:
    _has_real_keyring = False


@pytest.mark.skipif(
    not _has_real_keyring,
    reason="No real keyring backend available (headless/CI environment)"
)
def test_keyring_add_get_delete_roundtrip():
    from credential_bridge.backends.keyring import KeyringBackend
    backend = KeyringBackend(service_name="cb_integration_test")
    secret = {"token": "test_value_123"}
    backend.add_secret("cb_test_key", secret)
    result = backend.get_secret("cb_test_key")
    assert result == secret
    backend.delete_secret("cb_test_key")
