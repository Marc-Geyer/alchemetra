"""Application entry point.

Run with::

    python -m alchemetra.ui.app

or via the ``alchemetra`` console script (see ``pyproject.toml``).
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .context import UiContext
from .main_window import MainWindow


def main(argv: list[str] | None = None) -> int:
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("Alchemetra")
    app.setOrganizationName("Alchemetra")

    window = MainWindow(UiContext())
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
