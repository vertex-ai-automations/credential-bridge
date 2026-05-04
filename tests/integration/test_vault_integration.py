# tests/integration/test_vault_integration.py
import os
import pytest

pytestmark = pytest.mark.integration

VAULT_ADDR = os.environ.get("VAULT_ADDR")
VAULT_TOKEN = os.environ.get("VAULT_TOKEN")


@pytest.mark.skipif(
    not (VAULT_ADDR and VAULT_TOKEN),
    reason="VAULT_ADDR and VAULT_TOKEN environment variables required"
)
def test_vault_add_and_get_roundtrip():
    from credential_bridge.backends.vault import VaultBackend
    backend = VaultBackend(vault_url=VAULT_ADDR, vault_token=VAULT_TOKEN)
    backend.add_secret("ci/test", {"ci_key": "ci_value"})
    try:
        result = backend.get_secret("ci/test")
        assert result["ci_key"] == "ci_value"
    finally:
        backend.delete_secret("ci/test")
