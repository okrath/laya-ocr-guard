import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def isolate_guard_home(tmp_path_factory, monkeypatch):
    """Registry, refresh state and global hooks dir live in a throwaway GUARD_HOME."""
    monkeypatch.setenv("GUARD_HOME", str(tmp_path_factory.mktemp("guard_home")))


@pytest.fixture(autouse=True)
def isolate_global_guard_config(tmp_path_factory):
    """
    Ensure unit and integration tests do not accidentally read or mutate
    the host user's personal ~/.guard/config.json configuration.
    """
    dummy_dir = tmp_path_factory.mktemp("dummy_guard_home")
    dummy_config = dummy_dir / "nonexistent_config.json"
    dummy_session = dummy_dir / "active_session.json"
    with patch("guard.core.config.get_global_config_path", return_value=dummy_config), \
         patch("guard.core.session.SessionManager._get_global_active_session_file", return_value=dummy_session):
        yield
