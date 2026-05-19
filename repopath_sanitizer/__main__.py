from __future__ import annotations

import sys

from .cli import build_parser, run_cli
from .constants import APP_NAME, ORG_NAME


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.cli:
        return run_cli(args)

    from PyQt6.QtWidgets import QApplication

    from .ui_main import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
