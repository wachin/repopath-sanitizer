from __future__ import annotations

import sys
from PyQt6.QtWidgets import QApplication

from .cli import build_parser, run_cli
from .constants import APP_NAME, ORG_NAME
from .ui_main import MainWindow

def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.cli:
        return run_cli(args)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    w = MainWindow()
    w.show()
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())
