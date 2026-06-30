from __future__ import annotations

import os
import sys

from .cli import build_parser, run_cli
from .constants import APP_NAME, ORG_NAME
from .diagnostics import log_exception, log_info


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

    from PyQt6.QtWidgets import QApplication

    from .ui_main import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
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
