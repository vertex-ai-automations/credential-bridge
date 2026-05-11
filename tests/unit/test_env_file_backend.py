# tests/unit/test_env_file_backend.py
import pytest
from pathlib import Path
from credential_bridge.backends.env_file import EnvFileBackend
from credential_bridge.exceptions import EnvFileError, EnvFileNotFoundError


@pytest.fixture
def backend(tmp_path):
    return EnvFileBackend(path=tmp_path / ".env")


@pytest.fixture
def populated_backend(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("EXISTING=value\n", encoding="utf-8")
    return EnvFileBackend(path=env_file)


def test_backend_name():
    assert EnvFileBackend.backend_name == "env"


def test_add_secret_creates_file(backend, tmp_path):
    backend.add_secret("DB_HOST", {"DB_HOST": "localhost"})
    content = (tmp_path / ".env").read_text()
    assert "DB_HOST=localhost" in content


def test_add_secret_writes_group_comment(backend, tmp_path):
    backend.add_secret("database", {"DB_HOST": "localhost", "DB_PORT": "5432"})
    content = (tmp_path / ".env").read_text()
    assert "# database" in content
    assert "DB_HOST=localhost" in content
    assert "DB_PORT=5432" in content


def test_add_secret_raises_if_key_exists(populated_backend):
    from credential_bridge.exceptions import EnvFileKeyExistsError
    with pytest.raises(EnvFileKeyExistsError):
        populated_backend.add_secret("EXISTING", {"EXISTING": "new_value"})


def test_get_secret_returns_dict(populated_backend):
    result = populated_backend.get_secret("EXISTING")
    assert result == {"EXISTING": "value"}


def test_get_secret_raises_if_not_found(populated_backend):
    with pytest.raises(EnvFileNotFoundError):
        populated_backend.get_secret("MISSING")


def test_update_secret_changes_value(populated_backend, tmp_path):
    populated_backend.update_secret("EXISTING", {"EXISTING": "updated"})
    content = (tmp_path / ".env").read_text()
    assert "EXISTING=updated" in content
    assert "EXISTING=value" not in content


def test_update_secret_is_partial(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("A=1\nB=2\n", encoding="utf-8")
    backend = EnvFileBackend(path=env_file)
    backend.update_secret("A", {"A": "updated"})
    content = env_file.read_text()
    assert "A=updated" in content
    assert "B=2" in content


def test_update_secret_raises_if_no_key_exists(backend):
    with pytest.raises(EnvFileNotFoundError, match="not found"):
        backend.update_secret("MISSING", {"MISSING": "val"})


def test_delete_secret(populated_backend, tmp_path):
    populated_backend.delete_secret("EXISTING")
    content = (tmp_path / ".env").read_text()
    assert "EXISTING" not in content


def test_delete_secret_raises_if_not_found(populated_backend):
    with pytest.raises(EnvFileNotFoundError):
        populated_backend.delete_secret("MISSING")


def test_list_secrets(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("A=1\nB=2\nC=3\n", encoding="utf-8")
    backend = EnvFileBackend(path=env_file)
    assert sorted(backend.list_secrets()) == ["A", "B", "C"]


def test_load_into_environ_on_add(tmp_path, monkeypatch):
    import os
    env_file = tmp_path / ".env"
    backend = EnvFileBackend(path=env_file, load_into_environ=True)
    backend.add_secret("MY_VAR", {"MY_VAR": "hello"})
    assert os.environ.get("MY_VAR") == "hello"
    monkeypatch.delenv("MY_VAR", raising=False)


def test_write_uses_tmp_file(backend, tmp_path, mocker):
    """Verify atomic write: .env.tmp is created then renamed."""
    written_paths = []
    original_write = Path.write_text

    def track_write(self, *args, **kwargs):
        written_paths.append(str(self))
        return original_write(self, *args, **kwargs)

    mocker.patch.object(Path, "write_text", track_write)
    backend.add_secret("KEY", {"KEY": "val"})
    assert any(".env.tmp" in p for p in written_paths)


def test_add_secret_quotes_value_with_spaces(backend, tmp_path):
    backend.add_secret("GREETING", {"GREETING": "hello world"})
    content = (tmp_path / ".env").read_text()
    assert 'GREETING="hello world"' in content
    # Reading it back should return the unquoted value
    result = backend.get_secret("GREETING")
    assert result == {"GREETING": "hello world"}


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
    with pytest.raises(EnvFileNotFoundError):
        backend.get_secret("DB_HOST")


def test_env_multi_key_group(tmp_path):
    from credential_bridge.backends.env_file import EnvFileBackend
    backend = EnvFileBackend(path=tmp_path / ".env")

    backend.add_secret("database", {"DB_HOST": "localhost", "DB_PORT": "5432"})
    assert backend.get_secret("DB_HOST") == {"DB_HOST": "localhost"}
    assert backend.get_secret("DB_PORT") == {"DB_PORT": "5432"}
    assert "DB_HOST" in backend.list_secrets()
    assert "DB_PORT" in backend.list_secrets()


def test_get_secret_by_group_name(tmp_path):
    """get_secret with a group label returns all keys under that # comment block."""
    backend = EnvFileBackend(path=tmp_path / ".env")
    backend.add_secret("database", {"DB_HOST": "localhost", "DB_PORT": "5432"})
    result = backend.get_secret("database")
    assert result == {"DB_HOST": "localhost", "DB_PORT": "5432"}


def test_delete_secret_by_group_name(tmp_path):
    """delete_secret with a group label removes all keys and the comment header."""
    backend = EnvFileBackend(path=tmp_path / ".env")
    backend.add_secret("database", {"DB_HOST": "localhost", "DB_PORT": "5432"})
    backend.delete_secret("database")
    with pytest.raises(EnvFileNotFoundError):
        backend.get_secret("DB_HOST")
    with pytest.raises(EnvFileNotFoundError):
        backend.get_secret("DB_PORT")
    content = (tmp_path / ".env").read_text()
    assert "# database" not in content
    assert "DB_HOST" not in content


def test_delete_secret_by_group_name_raises_if_group_missing(backend):
    with pytest.raises(EnvFileNotFoundError):
        backend.delete_secret("nonexistent_group")


def test_load_into_environ_on_update(tmp_path, monkeypatch):
    import os
    env_file = tmp_path / ".env"
    env_file.write_text("MY_VAR=hello\n", encoding="utf-8")
    backend = EnvFileBackend(path=env_file, load_into_environ=True)
    backend.update_secret("MY_VAR", {"MY_VAR": "world"})
    assert os.environ.get("MY_VAR") == "world"
    monkeypatch.delenv("MY_VAR", raising=False)


def test_load_into_environ_on_delete(tmp_path, monkeypatch):
    import os
    env_file = tmp_path / ".env"
    env_file.write_text("MY_VAR=hello\n", encoding="utf-8")
    monkeypatch.setenv("MY_VAR", "hello")
    backend = EnvFileBackend(path=env_file, load_into_environ=True)
    backend.delete_secret("MY_VAR")
    assert os.environ.get("MY_VAR") is None
