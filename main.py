from __future__ import annotations

import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from pomodoro.main_window import MainWindow, load_application_fonts, resource_path


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Pomodoro Timer")
    app.setOrganizationName("Pomodoro Timer")
    load_application_fonts()

    stylesheet = resource_path("pomodoro/styles.qss").read_text(encoding="utf-8")
    app.setStyleSheet(stylesheet)
    app.setFont(QFont("JetBrains Mono", 10))
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
