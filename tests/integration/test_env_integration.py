# tests/integration/test_env_integration.py
import pytest

pytestmark = pytest.mark.integration


def test_env_full_crud(tmp_path):
    from credential_bridge.backends.env_file import EnvFileBackend
    backend = EnvFileBackend(path=tmp_path / ".env")

    # Add
    backend.add_secret("DB_HOST", {"DB_HOST": "localhost"})
    assert backend.get_secret("DB_HOST") == {"DB_HOST": "localhost"}

    # Update
    backend.update_secret("DB_HOST", {"DB_HOST": "remotehost"})
    assert backend.get_secret("DB_HOST") == {"DB_HOST": "remotehost"}

    # List
    assert "DB_HOST" in backend.list_secrets()

    # Delete
    backend.delete_secret("DB_HOST")
    with pytest.raises(Exception):
        backend.get_secret("DB_HOST")


def test_env_multi_key_group(tmp_path):
    from credential_bridge.backends.env_file import EnvFileBackend
    backend = EnvFileBackend(path=tmp_path / ".env")

    backend.add_secret("database", {"DB_HOST": "localhost", "DB_PORT": "5432"})
    assert backend.get_secret("DB_HOST") == {"DB_HOST": "localhost"}
    assert backend.get_secret("DB_PORT") == {"DB_PORT": "5432"}
    assert "DB_HOST" in backend.list_secrets()
    assert "DB_PORT" in backend.list_secrets()
