from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QFontDatabase, QMouseEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSpacerItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .model import Mode, PomodoroModel, Task


def resource_path(relative_path: str) -> Path:
    import sys

    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / relative_path


def load_application_fonts() -> None:
    for font_path in (
        resource_path("assets/fonts/Aleo-Regular.ttf"),
        resource_path("assets/fonts/JetBrainsMono-Regular.ttf"),
    ):
        if QFontDatabase.addApplicationFont(str(font_path)) < 0:
            raise RuntimeError(f"Could not load application font: {font_path}")


class TaskTitleLabel(QLabel):
    def __init__(self, task: Task, select_task: Callable[[], None]) -> None:
        super().__init__(task.title)
        self.setObjectName("taskTitle")
        self.setWordWrap(True)
        self.setProperty("completed", task.completed)
        self._select_task = select_task
        self.setCursor(Qt.CursorShape.PointingHandCursor if not task.completed else Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if not self.property("completed") and event.button() == Qt.MouseButton.LeftButton:
            self._select_task()
        super().mousePressEvent(event)


class TaskDialog(QDialog):
    def __init__(self, parent: QWidget, task: Task | None = None, projects: list[str] | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit task" if task else "Make a little plan")
        self.setModal(True)
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.title_input = QLineEdit(task.title if task else "")
        self.title_input.setMaxLength(120)
        self.title_input.setPlaceholderText("What would you like to work on?")
        self.note_input = QTextEdit(task.note if task else "")
        self.note_input.setMaximumHeight(90)
        self.note_input.setPlaceholderText("A detail, reminder, or first step…")
        self.project_input = QComboBox()
        self.project_input.setEditable(True)
        self.project_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.project_input.addItems(sorted(set(projects or []), key=str.casefold))
        self.project_input.setCurrentText(task.project if task else "")
        self.project_input.lineEdit().setMaxLength(60)
        self.estimate_input = QSpinBox()
        self.estimate_input.setRange(1, 12)
        self.estimate_input.setValue(task.estimate if task else 1)
        self.error_label = QLabel()
        self.error_label.setObjectName("errorLabel")
        self.error_label.setWordWrap(True)

        form.addRow("Task name", self.title_input)
        form.addRow("Note (optional)", self.note_input)
        form.addRow("Project (optional)", self.project_input)
        form.addRow("Estimated pomodoros", self.estimate_input)
        layout.addLayout(form)
        layout.addWidget(self.error_label)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.title_input.setFocus()

    def values(self) -> tuple[str, str, str, int]:
        return (
            self.title_input.text().strip(),
            self.note_input.toPlainText().strip(),
            self.project_input.currentText().strip(),
            self.estimate_input.value(),
        )

    def accept(self) -> None:
        if not self.title_input.text().strip():
            self.error_label.setText("Enter a task name to continue.")
            self.title_input.setFocus()
            return
        if len(self.note_input.toPlainText()) > 500:
            self.error_label.setText("Task notes must be 500 characters or fewer.")
            return
        if len(self.project_input.currentText()) > 60:
            self.error_label.setText("Project names must be 60 characters or fewer.")
            return
        super().accept()


class MainWindow(QMainWindow):
    def __init__(self, model: PomodoroModel | None = None) -> None:
        super().__init__()
        self.model = model or PomodoroModel()
        self.setWindowTitle("Pomodoro Timer")
        self.resize(820, 900)
        self.setMinimumSize(640, 680)
        self._status_text = "Ready when you are"
        self.mode_buttons: dict[str, QPushButton] = {}
        self.filter_buttons: dict[str, QPushButton] = {}

        self.clock = QTimer(self)
        self.clock.setInterval(250)
        self.clock.timeout.connect(self._tick)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        page = QWidget()
        page.setMaximumWidth(768)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(24, 22, 24, 30)
        page_layout.setSpacing(0)
        page_layout.addWidget(self._build_header())
        page_layout.addSpacing(22)
        page_layout.addWidget(
            self._build_timer(), alignment=Qt.AlignmentFlag.AlignHCenter
        )
        page_layout.addSpacing(30)
        page_layout.addWidget(self._build_tasks())
        page_layout.addStretch(1)
        scroll.setWidget(page)
        scroll_layout = QVBoxLayout()
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.addWidget(scroll)
        central = QWidget()
        central.setLayout(scroll_layout)
        self.setCentralWidget(central)
        self._refresh_all()

    def _build_header(self) -> QWidget:
        header = QWidget()
        layout = QVBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        title = QLabel("Pomodoro Timer")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        intro = QLabel(
            "Plan tasks, organize projects, track focus sessions, and make time for restorative breaks."
        )
        intro.setObjectName("intro")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        return header

    def _build_timer(self) -> QWidget:
        wrapper = QWidget()
        wrapper.setMaximumWidth(372)
        outer = QVBoxLayout(wrapper)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(12)

        panel = QFrame()
        panel.setObjectName("timerPanel")
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)
        eyebrow = QLabel("FOCUS, THEN REST")
        eyebrow.setObjectName("eyebrow")
        eyebrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(eyebrow)

        tabs = QHBoxLayout()
        tabs.setSpacing(6)
        modes: tuple[tuple[Mode, str], ...] = (
            ("work", "Focus"),
            ("short", "Short break"),
            ("long", "Long break"),
        )
        for mode, label in modes:
            button = QPushButton(label)
            button.setObjectName("modeButton")
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, selected=mode: self._select_mode(selected))
            self.mode_buttons[mode] = button
            tabs.addWidget(button)
        layout.addLayout(tabs)

        self.timer_display = QLabel()
        self.timer_display.setObjectName("timerDisplay")
        self.timer_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_display.setFont(QFont("JetBrains Mono"))
        layout.addWidget(self.timer_display)

        self.timer_status = QLabel()
        self.timer_status.setObjectName("timerStatus")
        self.timer_status.setMinimumHeight(24)
        self.timer_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.timer_status)

        controls = QHBoxLayout()
        controls.setAlignment(Qt.AlignmentFlag.AlignCenter)
        controls.setSpacing(10)
        self.start_button = QPushButton()
        self.start_button.setObjectName("primaryButton")
        self.start_button.setMinimumWidth(128)
        self.start_button.clicked.connect(self._toggle_timer)
        reset_button = QPushButton("Reset")
        reset_button.clicked.connect(self._reset_timer)
        controls.addWidget(self.start_button)
        controls.addWidget(reset_button)
        layout.addLayout(controls)

        outer.addWidget(panel, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.session_count = QLabel()
        self.session_count.setObjectName("sessionCount")
        self.session_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(self.session_count)
        self.current_focus = QLabel()
        self.current_focus.setObjectName("currentFocus")
        self.current_focus.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.current_focus.setWordWrap(True)
        outer.addWidget(self.current_focus)
        self.storage_notice = QLabel()
        self.storage_notice.setObjectName("storageNotice")
        self.storage_notice.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.storage_notice.setWordWrap(True)
        outer.addWidget(self.storage_notice)
        return wrapper

    def _build_tasks(self) -> QWidget:
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        heading_row = QHBoxLayout()
        heading = QLabel("Your tasks")
        heading.setObjectName("taskHeading")
        heading_row.addWidget(heading)
        heading_row.addItem(QSpacerItem(20, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        add_button = QPushButton("+ Add a task")
        add_button.setObjectName("addTaskButton")
        add_button.clicked.connect(self._add_task)
        heading_row.addWidget(add_button)
        layout.addLayout(heading_row)

        tools = QHBoxLayout()
        self.project_filter = QComboBox()
        self.project_filter.currentIndexChanged.connect(self._render_tasks)
        tools.addWidget(self.project_filter)
        tools.addStretch(1)
        filters = QHBoxLayout()
        for filter_id, text in (("active", "To do"), ("completed", "Completed"), ("all", "All")):
            button = QPushButton(text)
            button.setObjectName("filterButton")
            button.setCheckable(True)
            button.setChecked(filter_id == "active")
            button.clicked.connect(lambda checked=False, selected=filter_id: self._set_filter(selected))
            self.filter_buttons[filter_id] = button
            filters.addWidget(button)
        tools.addLayout(filters)
        layout.addLayout(tools)

        self.task_list = QVBoxLayout()
        self.task_list.setContentsMargins(0, 0, 0, 0)
        self.task_list.setSpacing(7)
        layout.addLayout(self.task_list)
        self.empty_tasks = QLabel()
        self.empty_tasks.setObjectName("currentFocus")
        self.empty_tasks.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_tasks.setWordWrap(True)
        self.empty_tasks.setContentsMargins(16, 22, 16, 22)
        layout.addWidget(self.empty_tasks)
        self.task_count = QLabel()
        self.task_count.setObjectName("taskCount")
        layout.addWidget(self.task_count)
        self.task_filter = "active"
        return section

    def _select_mode(self, mode: Mode) -> None:
        self.model.select_mode(mode)
        self.clock.stop()
        self._status_text = "Ready when you are" if mode == "work" else "Take a little breather"
        self._refresh_timer()

    def _toggle_timer(self) -> None:
        self.model.toggle_timer()
        self._status_text = self.model.last_timer_event
        if self.model.running:
            self.clock.start()
        else:
            self.clock.stop()
        self._refresh_timer()

    def _tick(self) -> None:
        completed = self.model.update_timer()
        if completed:
            self.clock.stop()
            self._status_text = self.model.last_timer_event
            self._refresh_all()
        else:
            self._refresh_timer()

    def _reset_timer(self) -> None:
        self.model.reset_timer()
        self.clock.stop()
        self._status_text = "Ready when you are" if self.model.mode == "work" else "Take a little breather"
        self._refresh_timer()

    def _set_filter(self, filter_id: str) -> None:
        self.task_filter = filter_id
        for key, button in self.filter_buttons.items():
            button.setChecked(key == filter_id)
        self._render_tasks()

    def _add_task(self) -> None:
        dialog = TaskDialog(self, projects=self.model.projects)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            task = self.model.add_task(*dialog.values())
        except ValueError as error:
            QMessageBox.warning(self, "Could not add task", str(error))
            return
        self.task_filter = "active"
        self.filter_buttons["active"].setChecked(True)
        self.project_filter.setCurrentIndex(0)
        self._status_text = f"Ready to focus on {task.title}"
        self._refresh_all()

    def _edit_task(self, task: Task) -> None:
        dialog = TaskDialog(self, task, self.model.projects)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.model.edit_task(task.id, *dialog.values())
        except ValueError as error:
            QMessageBox.warning(self, "Could not edit task", str(error))
            return
        self._refresh_all()

    def _delete_task(self, task: Task) -> None:
        answer = QMessageBox.question(
            self,
            "Delete task",
            f"Delete “{task.title}”?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.model.delete_task(task.id)
            self._refresh_all()

    def _refresh_all(self) -> None:
        self._refresh_timer()
        self._render_tasks()
        self.storage_notice.setText(self.model.storage_notice or "")
        self.storage_notice.setVisible(bool(self.model.storage_notice))

    def _refresh_timer(self) -> None:
        minutes, seconds = divmod(self.model.remaining, 60)
        self.timer_display.setText(f"{minutes:02d}:{seconds:02d}")
        self.timer_status.setText(self._status_text)
        self.start_button.setText(
            "Pause" if self.model.running else ("Start focus" if self.model.mode == "work" else "Start break")
        )
        for key, button in self.mode_buttons.items():
            button.setChecked(key == self.model.mode)
        self.session_count.setText(
            f"{self.model.completed_focus_sessions} of 4 focus sessions completed"
        )
        task = self.model.selected_task
        if task is None:
            self.current_focus.setText(
                "Up next: Choose a task to begin · Your next 25 minutes are yours."
            )
        else:
            project = f"{task.project} · " if task.project else ""
            self.current_focus.setText(
                f"Up next: {task.title} · {project}{task.pomodoros} of {task.estimate} pomodoros"
            )

    def _render_tasks(self) -> None:
        selected_project = self.project_filter.currentData()
        self.project_filter.blockSignals(True)
        self.project_filter.clear()
        self.project_filter.addItem("All projects", "all")
        project_names = sorted(
            set(self.model.projects + [task.project for task in self.model.tasks if task.project]),
            key=str.casefold,
        )
        for name in project_names:
            self.project_filter.addItem(name, name)
        index = self.project_filter.findData(selected_project)
        self.project_filter.setCurrentIndex(max(0, index))
        self.project_filter.blockSignals(False)

        while self.task_list.count():
            item = self.task_list.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        project = self.project_filter.currentData()
        visible = [
            task for task in self.model.tasks
            if (self.task_filter == "all" or
                (self.task_filter == "completed" and task.completed) or
                (self.task_filter == "active" and not task.completed))
            and (project == "all" or task.project == project)
        ]
        for task in visible:
            self.task_list.addWidget(self._task_card(task))
        has_tasks = bool(visible)
        self.empty_tasks.setVisible(not has_tasks)
        if not self.model.tasks:
            self.empty_tasks.setText("✳\nA fresh start.\nAdd a task and give your focus somewhere to go.")
        elif not has_tasks:
            self.empty_tasks.setText("Nothing here just yet.\nTry another filter or add a new task.")
        active_count = sum(not task.completed for task in self.model.tasks)
        project_count = len(self.model.projects)
        task_label = "task left" if active_count == 1 else "tasks left"
        project_label = "project" if project_count == 1 else "projects"
        suffix = f" · {project_count} {project_label}" if project_count else ""
        self.task_count.setText(f"{active_count} {task_label}{suffix}")
        self._refresh_timer()

    def _task_card(self, task: Task) -> QFrame:
        card = QFrame()
        card.setObjectName("taskCard")
        card.setProperty("selected", task.id == self.model.selected_task_id)
        card.setProperty("completed", task.completed)
        row = QHBoxLayout(card)
        row.setContentsMargins(12, 10, 12, 10)
        row.setSpacing(10)

        check = QCheckBox()
        check.setChecked(task.completed)
        check.setToolTip("Mark task as not completed" if task.completed else "Mark task as completed")
        check.clicked.connect(lambda checked=False, task_id=task.id: self._toggle_task(task_id))
        row.addWidget(check, alignment=Qt.AlignmentFlag.AlignTop)

        details = QVBoxLayout()
        details.setSpacing(4)
        title = TaskTitleLabel(task, lambda: self._select_task(task.id))
        details.addWidget(title)
        project = f"{task.project} · " if task.project else ""
        meta = QLabel(f"{project}{task.pomodoros} / {task.estimate} pomodoros")
        meta.setObjectName("taskMeta")
        details.addWidget(meta)
        if task.note:
            note = QLabel(task.note)
            note.setObjectName("taskNote")
            note.setWordWrap(True)
            details.addWidget(note)
        row.addLayout(details, stretch=1)

        if task.id == self.model.selected_task_id:
            selected = QLabel("Selected")
            selected.setObjectName("taskMeta")
            row.addWidget(selected)
        edit_button = QPushButton("Edit")
        edit_button.setObjectName("editTaskButton")
        edit_button.clicked.connect(lambda checked=False, selected_task=task: self._edit_task(selected_task))
        row.addWidget(edit_button)
        delete_button = QPushButton("Delete")
        delete_button.setObjectName("deleteTaskButton")
        delete_button.clicked.connect(lambda checked=False, selected_task=task: self._delete_task(selected_task))
        row.addWidget(delete_button)
        return card

    def _select_task(self, task_id: str) -> None:
        self.model.select_task(task_id)
        task = self.model.selected_task
        if task is not None:
            self._status_text = f"Ready to focus on {task.title}"
        self._refresh_all()

    def _toggle_task(self, task_id: str) -> None:
        self.model.toggle_task(task_id)
        self._refresh_all()
