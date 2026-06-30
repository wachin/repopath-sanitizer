from __future__ import annotations

import logging
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from .constants import APP_ID
from .state import get_state_dir


_LOGGER_NAME = APP_ID
_LOGGER: Optional[logging.Logger] = None
_SESSION_LOG_PATH: Optional[Path] = None


def _build_session_log_path() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        base_dir = get_state_dir()
    except OSError:
        base_dir = Path(tempfile.gettempdir()) / APP_ID
        base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / f"session-{stamp}.log"


def get_logger() -> logging.Logger:
    global _LOGGER, _SESSION_LOG_PATH
    if _LOGGER is not None:
        return _LOGGER

    _SESSION_LOG_PATH = _build_session_log_path()
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    logger.propagate = False

    try:
        handler = logging.FileHandler(_SESSION_LOG_PATH, encoding="utf-8")
    except OSError:
        fallback_dir = Path(tempfile.gettempdir()) / APP_ID
        fallback_dir.mkdir(parents=True, exist_ok=True)
        _SESSION_LOG_PATH = fallback_dir / _SESSION_LOG_PATH.name
        handler = logging.FileHandler(_SESSION_LOG_PATH, encoding="utf-8")
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)

    _LOGGER = logger
    logger.info("Logging initialized at %s", _SESSION_LOG_PATH)
    return logger


def session_log_path() -> Path:
    get_logger()
    assert _SESSION_LOG_PATH is not None
    return _SESSION_LOG_PATH


def log_info(message: str, *args) -> None:
    get_logger().info(message, *args)


def log_warning(message: str, *args) -> None:
    get_logger().warning(message, *args)


def log_error(message: str, *args) -> None:
    get_logger().error(message, *args)


def log_exception(message: str, *args) -> None:
    get_logger().exception(message, *args)


def save_log_copy(destination: Path) -> Path:
    source = session_log_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    get_logger().info("Saved log copy to %s", destination)
    return destination


def reset_logging_for_tests() -> None:
    global _LOGGER, _SESSION_LOG_PATH
    if _LOGGER is not None:
        for handler in list(_LOGGER.handlers):
            handler.close()
            _LOGGER.removeHandler(handler)
    _LOGGER = None
    _SESSION_LOG_PATH = None
