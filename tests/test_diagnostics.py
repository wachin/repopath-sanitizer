import importlib
from pathlib import Path


def test_save_log_copy_writes_session_log(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))

    import repopath_sanitizer.state as state
    import repopath_sanitizer.diagnostics as diagnostics

    importlib.reload(state)
    importlib.reload(diagnostics)
    diagnostics.reset_logging_for_tests()

    diagnostics.log_info("hello %s", "world")
    destination = tmp_path / "exported" / "session.log"
    saved = diagnostics.save_log_copy(destination)

    assert saved == destination
    assert destination.exists()
    content = destination.read_text(encoding="utf-8")
    assert "Logging initialized" in content
    assert "hello world" in content

    diagnostics.reset_logging_for_tests()
