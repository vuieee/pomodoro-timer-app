from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from pomodoro.main_window import MainWindow, load_application_fonts, resource_path
from pomodoro.model import PomodoroModel
from pomodoro.storage import JsonStore


class MainWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        load_application_fonts()
        cls.app.setStyleSheet(resource_path("pomodoro/styles.qss").read_text(encoding="utf-8"))

    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        model = PomodoroModel(JsonStore(Path(self.directory.name) / "data.json"))
        self.window = MainWindow(model)

    def tearDown(self) -> None:
        self.window.close()
        self.directory.cleanup()

    def test_timer_mode_switch_updates_native_controls(self) -> None:
        self.window._select_mode("short")
        self.assertEqual(self.window.model.remaining, 5 * 60)
        self.assertEqual(self.window.timer_display.text(), "05:00")
        self.assertTrue(self.window.mode_buttons["short"].isChecked())
        self.assertFalse(self.window.model.running)

    def test_project_and_status_filters_render_task_cards(self) -> None:
        self.window.model.add_task("Draft report", "Outline first", "Work", 2)
        self.window._refresh_all()
        self.assertEqual(self.window.project_filter.findData("Work"), 1)
        self.assertEqual(self.window.task_list.count(), 1)

        self.window._set_filter("completed")
        self.assertEqual(self.window.task_list.count(), 0)
        self.assertFalse(self.window.empty_tasks.isHidden())

        self.window.model.toggle_task(self.window.model.tasks[0].id)
        self.window._set_filter("completed")
        self.assertEqual(self.window.task_list.count(), 1)
        self.assertTrue(self.window.empty_tasks.isHidden())


if __name__ == "__main__":
    unittest.main()
