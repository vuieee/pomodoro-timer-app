from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pomodoro.model import DURATIONS, PomodoroModel
from pomodoro.storage import JsonStore


class PomodoroModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.store = JsonStore(Path(self.directory.name) / "data.json")
        self.model = PomodoroModel(self.store)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_task_creation_editing_completion_and_deletion(self) -> None:
        task = self.model.add_task("  Write tests  ", "  First step  ", "Project A", 3)
        self.assertEqual(task.title, "Write tests")
        self.assertEqual(self.model.selected_task_id, task.id)
        self.model.edit_task(task.id, "Write model tests", "Cover timer cycles", "Project B", 4)
        self.assertEqual((task.title, task.note, task.project, task.estimate),
                         ("Write model tests", "Cover timer cycles", "Project B", 4))
        self.assertEqual(self.model.projects, ["Project B"])
        self.model.toggle_task(task.id)
        self.assertTrue(task.completed)
        self.assertIsNone(self.model.selected_task)
        self.model.toggle_task(task.id)
        self.assertFalse(task.completed)
        self.model.delete_task(task.id)
        self.assertEqual(self.model.tasks, [])
        self.assertEqual(self.model.projects, [])

    def test_rejects_invalid_tasks(self) -> None:
        for args in (("", "", "", 1), ("valid", "", "", 13)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.model.add_task(*args)

    def test_focus_cycles_to_long_break_and_resets_after_fourth_break(self) -> None:
        task = self.model.add_task("Read")
        now = 0.0
        for completed in range(1, 5):
            self.assertEqual(self.model.mode, "work")
            self.model.toggle_timer(now)
            now += DURATIONS["work"]
            self.assertTrue(self.model.update_timer(now))
            self.assertEqual(self.model.mode, "long" if completed == 4 else "short")
            self.assertEqual(self.model.completed_focus_sessions, completed)
            self.assertEqual(self.model.total_focus_sessions, completed)
            self.assertEqual(task.pomodoros, completed)
            self.model.toggle_timer(now)
            now += DURATIONS[self.model.mode]
            self.assertTrue(self.model.update_timer(now))
        self.assertEqual(self.model.mode, "work")
        self.assertEqual(self.model.completed_focus_sessions, 0)

    def test_pause_resume_reset_and_mode_switch(self) -> None:
        self.model.toggle_timer(10.0)
        self.assertEqual(self.model.remaining, DURATIONS["work"])
        self.model.toggle_timer(20.5)
        self.assertEqual(self.model.remaining, DURATIONS["work"] - 10)
        self.assertFalse(self.model.running)
        self.model.toggle_timer(30.0)
        self.model.reset_timer()
        self.assertEqual(self.model.remaining, DURATIONS["work"])
        self.model.select_mode("short")
        self.assertEqual(self.model.remaining, DURATIONS["short"])
        self.assertFalse(self.model.running)

    def test_data_survives_reload(self) -> None:
        task = self.model.add_task("Persist me", "Details", "Home", 2)
        reloaded = PomodoroModel(self.store)
        self.assertEqual(reloaded.tasks[0].to_data(), task.to_data())
        self.assertEqual(reloaded.selected_task_id, task.id)
        self.assertEqual(reloaded.projects, ["Home"])

    def test_malformed_json_is_reported_without_being_overwritten(self) -> None:
        self.store.path.write_text("{", encoding="utf-8")
        loaded = PomodoroModel(self.store)
        self.assertTrue(loaded.storage_notice)
        self.assertEqual(self.store.path.read_text(encoding="utf-8"), "{")

    def test_invalid_utf8_is_reported_without_being_overwritten(self) -> None:
        self.store.path.write_bytes(b"\xff")
        loaded = PomodoroModel(self.store)
        self.assertTrue(loaded.storage_notice)
        self.assertEqual(self.store.path.read_bytes(), b"\xff")

    def test_saved_data_is_sanitized(self) -> None:
        self.store.path.write_text(json.dumps({
            "tasks": [
                {"id": "ok", "title": "valid", "estimate": 100, "pomodoros": -2},
                {"title": "missing id"},
            ],
            "completedFocusSessions": 99,
        }), encoding="utf-8")
        loaded = PomodoroModel(self.store)
        self.assertEqual(len(loaded.tasks), 1)
        self.assertEqual(loaded.tasks[0].estimate, 12)
        self.assertEqual(loaded.tasks[0].pomodoros, 0)
        self.assertEqual(loaded.completed_focus_sessions, 4)


if __name__ == "__main__":
    unittest.main()
