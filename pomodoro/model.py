from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass
from typing import Any, Literal

from .storage import JsonStore

Mode = Literal["work", "short", "long"]

DURATIONS: dict[Mode, int] = {"work": 25 * 60, "short": 5 * 60, "long": 15 * 60}
LABELS: dict[Mode, str] = {"work": "Focus", "short": "Short break", "long": "Long break"}


@dataclass(slots=True)
class Task:
    id: str
    title: str
    note: str = ""
    project: str = ""
    estimate: int = 1
    pomodoros: int = 0
    completed: bool = False

    @classmethod
    def from_data(cls, value: Any) -> Task | None:
        if not isinstance(value, dict) or not isinstance(value.get("id"), str):
            return None
        if not isinstance(value.get("title"), str) or not value["title"].strip():
            return None
        estimate = value.get("estimate")
        pomodoros = value.get("pomodoros")
        return cls(
            id=value["id"],
            title=value["title"][:120],
            note=value.get("note", "")[:500] if isinstance(value.get("note"), str) else "",
            project=value.get("project", "")[:60] if isinstance(value.get("project"), str) else "",
            estimate=min(12, max(1, estimate)) if isinstance(estimate, int) and not isinstance(estimate, bool) else 1,
            pomodoros=max(0, pomodoros) if isinstance(pomodoros, int) and not isinstance(pomodoros, bool) else 0,
            completed=value.get("completed") is True,
        )

    def to_data(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "note": self.note,
            "project": self.project,
            "estimate": self.estimate,
            "pomodoros": self.pomodoros,
            "completed": self.completed,
        }


class PomodoroModel:
    def __init__(self, store: JsonStore | None = None) -> None:
        self.store = store or JsonStore()
        data, self.storage_notice = self.store.load()
        self.tasks = [
            task
            for value in data.get("tasks", [])
            if (task := Task.from_data(value)) is not None
        ] if isinstance(data.get("tasks", []), list) else []
        raw_projects = data.get("projects", [])
        self.projects = list(dict.fromkeys(
            project[:60] for project in raw_projects if isinstance(project, str)
        )) if isinstance(raw_projects, list) else []
        self.total_focus_sessions = self._nonnegative_integer(data.get("totalFocusSessions"))
        completed_sessions = data.get("completedFocusSessions")
        self.completed_focus_sessions = (
            min(4, max(0, completed_sessions))
            if isinstance(completed_sessions, int) and not isinstance(completed_sessions, bool)
            else 0
        )
        selected_id = data.get("selectedTaskId")
        self.selected_task_id = selected_id if any(
            task.id == selected_id and not task.completed for task in self.tasks
        ) else None
        self.mode: Mode = "work"
        self.remaining = DURATIONS[self.mode]
        self.running = False
        self.deadline: float | None = None
        self.last_timer_event = ""

    @staticmethod
    def _nonnegative_integer(value: Any) -> int:
        return max(0, value) if isinstance(value, int) and not isinstance(value, bool) else 0

    @property
    def selected_task(self) -> Task | None:
        return next(
            (task for task in self.tasks if task.id == self.selected_task_id and not task.completed),
            None,
        )

    def to_data(self) -> dict[str, Any]:
        return {
            "tasks": [task.to_data() for task in self.tasks],
            "projects": self.projects,
            "totalFocusSessions": self.total_focus_sessions,
            "completedFocusSessions": self.completed_focus_sessions,
            "selectedTaskId": self.selected_task_id,
        }

    def _persist(self) -> None:
        try:
            self.store.save(self.to_data())
        except OSError as error:
            self.storage_notice = f"Could not save your changes. Check the application data folder. ({error})"
        else:
            self.storage_notice = ""

    def add_task(
        self, title: str, note: str = "", project: str = "", estimate: int = 1
    ) -> Task:
        title = title.strip()
        note = note.strip()
        project = project.strip()
        if not title or len(title) > 120:
            raise ValueError("Task names must contain 1 to 120 characters.")
        if len(note) > 500:
            raise ValueError("Task notes must be 500 characters or fewer.")
        if len(project) > 60:
            raise ValueError("Project names must be 60 characters or fewer.")
        if not 1 <= estimate <= 12:
            raise ValueError("Estimated pomodoros must be between 1 and 12.")
        task = Task(uuid.uuid4().hex, title, note, project, estimate)
        self.tasks.insert(0, task)
        if project and project not in self.projects:
            self.projects.append(project)
        self.selected_task_id = task.id
        self._persist()
        return task

    def edit_task(self, task_id: str, title: str, note: str, project: str, estimate: int) -> None:
        task = self._find_task(task_id)
        title = title.strip()
        note = note.strip()
        project = project.strip()
        if not title or len(title) > 120:
            raise ValueError("Task names must contain 1 to 120 characters.")
        if len(note) > 500:
            raise ValueError("Task notes must be 500 characters or fewer.")
        if len(project) > 60:
            raise ValueError("Project names must be 60 characters or fewer.")
        if not 1 <= estimate <= 12:
            raise ValueError("Estimated pomodoros must be between 1 and 12.")
        previous_project = task.project
        task.title, task.note, task.project, task.estimate = title, note, project, estimate
        if project and project not in self.projects:
            self.projects.append(project)
        self._remove_unused_project(previous_project)
        self._persist()

    def select_task(self, task_id: str) -> None:
        task = next((item for item in self.tasks if item.id == task_id and not item.completed), None)
        if task is None:
            return
        self.selected_task_id = task_id
        self._persist()

    def toggle_task(self, task_id: str) -> None:
        task = self._find_task(task_id)
        task.completed = not task.completed
        if task.completed and self.selected_task_id == task_id:
            self.selected_task_id = None
        self._persist()

    def delete_task(self, task_id: str) -> None:
        task = self._find_task(task_id)
        self.tasks.remove(task)
        if self.selected_task_id == task_id:
            self.selected_task_id = None
        self._remove_unused_project(task.project)
        self._persist()

    def _find_task(self, task_id: str) -> Task:
        task = next((item for item in self.tasks if item.id == task_id), None)
        if task is None:
            raise ValueError("The selected task no longer exists.")
        return task

    def _remove_unused_project(self, project: str) -> None:
        if project and not any(task.project == project for task in self.tasks):
            self.projects = [name for name in self.projects if name != project]

    def select_mode(self, mode: Mode) -> None:
        if mode not in DURATIONS:
            raise ValueError(f"Unknown timer mode: {mode}")
        self.mode = mode
        self.running = False
        self.deadline = None
        self.remaining = DURATIONS[self.mode]
        self.last_timer_event = ""

    def reset_timer(self) -> None:
        self.running = False
        self.deadline = None
        self.remaining = DURATIONS[self.mode]
        self.last_timer_event = ""

    def toggle_timer(self, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        if self.running:
            self.remaining = max(0, math.ceil((self.deadline or now) - now))
            self.running = False
            self.deadline = None
            self.last_timer_event = "Timer paused"
            return
        self.deadline = now + self.remaining
        self.running = True
        self.last_timer_event = f"{LABELS[self.mode]} session in progress"

    def update_timer(self, now: float | None = None) -> bool:
        if not self.running:
            return False
        now = time.monotonic() if now is None else now
        self.remaining = max(0, math.ceil((self.deadline or now) - now))
        if self.remaining:
            return False
        self._finish_session()
        return True

    def _finish_session(self) -> None:
        completed_mode = self.mode
        self.running = False
        self.deadline = None
        if completed_mode == "work":
            self.completed_focus_sessions = min(4, self.completed_focus_sessions + 1)
            self.total_focus_sessions += 1
            if self.selected_task is not None:
                self.selected_task.pomodoros += 1
            self.mode = "long" if self.completed_focus_sessions == 4 else "short"
            self._persist()
        else:
            if completed_mode == "long":
                self.completed_focus_sessions = 0
                self._persist()
            self.mode = "work"
        self.remaining = DURATIONS[self.mode]
        self.last_timer_event = (
            f"{LABELS[completed_mode]} session complete. {LABELS[self.mode]} is ready"
        )
