# Pomodoro Timer

A native Windows desktop Pomodoro timer built with Python and PySide6. The interface follows the original app's dark palette, monospaced typography, and compact task cards without using a browser or embedded web view.

## Features

- 25-minute focus sessions, 5-minute short breaks, and 15-minute long breaks.
- A long break after every four completed focus sessions.
- Create, edit, complete, and delete tasks with notes, projects, and estimates.
- Filter tasks by project and status; track focus sessions against the selected task.
- Automatically save tasks and progress as JSON in the operating system's application-data directory.

Timer state resets when the app closes. Tasks, selected task, project names, completed focus sessions, and total focus sessions are saved.

## Run from source

1. Install Python 3.10 or later.
2. From the project directory, install the dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Launch the application:

   ```powershell
   python main.py
   ```

On Windows, application data is stored in `%APPDATA%\Pomodoro Timer\data.json`. macOS and Linux use their standard application-data directories.

## Tests

Run the model, timer-cycle, and persistence tests with:

```powershell
python -m unittest discover -s tests -v
```

## Build a Windows executable

Install the requirements, then run:

```powershell
python -m PyInstaller --clean --noconfirm pomodoro_timer.spec
```

The standalone executable is written to `dist\PomodoroTimer.exe`. The spec bundles the QSS stylesheet, only the Aleo and JetBrains Mono fonts used by the interface, and the JetBrains Mono font license.

## Project layout

```text
main.py                 Application entry point
pomodoro/
  main_window.py        PySide6 interface and interactions
  model.py              Task and timer behavior
  storage.py            JSON persistence and app-data paths
  styles.qss            Native Qt styling
assets/fonts/           Required desktop font files
tests/                  Model and persistence tests
pomodoro_timer.spec     PyInstaller one-file configuration
```
