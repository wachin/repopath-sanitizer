from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

from .cli import build_parser, run_cli
from .constants import APP_NAME, ORG_NAME
from .diagnostics import log_exception, log_info, log_warning


def _resolve_icon_path() -> Optional[Path]:
    """Return the first existing application icon path.

    Prefers the fancy icon shipped in ``data/icons/``, then the simpler
    ``data/repopath-sanitizer.svg``, then the system-installed icon used by
    the Debian package.  Works both when running from the source tree and
    when installed system-wide.
    """
    project_root = Path(__file__).resolve().parents[2]
    candidates = [
        # Source tree: fancy icon
        project_root / "data" / "icons" / "repopath-sanitizer.svg",
        # Source tree: simple icon
        project_root / "data" / "repopath-sanitizer.svg",
        # Relative to the current working directory
        Path("data/icons/repopath-sanitizer.svg"),
        Path("data/repopath-sanitizer.svg"),
        # Installed system icon (Debian package / desktop entry)
        Path("/usr/share/icons/hicolor/scalable/apps/repopath-sanitizer.svg"),
        Path("/usr/share/pixmaps/repopath-sanitizer.svg"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _configure_qt_platform_theme_for_gui() -> None:
    if sys.platform.startswith("linux"):
        current = os.environ.get("QT_QPA_PLATFORMTHEME", "")
        if current in {"", "qt5ct"}:
            os.environ["QT_QPA_PLATFORMTHEME"] = "gtk3"
            log_info("Set QT_QPA_PLATFORMTHEME=gtk3 for GUI startup (previous=%r)", current)
        else:
            log_info("Keeping existing QT_QPA_PLATFORMTHEME=%r", current)


def main() -> int:
    log_info("Application startup")
    parser = build_parser()
    args = parser.parse_args()
    log_info("Parsed arguments: cli=%s repo=%s", args.cli, args.repo)

    if args.cli:
        return run_cli(args)

    _configure_qt_platform_theme_for_gui()

    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import QApplication

    from .ui_main import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)

    icon_path = _resolve_icon_path()
    if icon_path is not None:
        app.setWindowIcon(QIcon(str(icon_path)))
        log_info("Application icon loaded: %s", icon_path)
    else:
        log_warning("Application icon not found; using default window icon")

    w = MainWindow()
    w.show()
    rc = app.exec()
    log_info("Application exit code=%s", rc)
    return rc

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        log_exception("Unhandled exception at process level")
        raise
