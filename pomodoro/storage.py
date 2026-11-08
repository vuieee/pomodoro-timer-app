from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


def app_data_directory() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "Pomodoro Timer"


class JsonStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or app_data_directory() / "data.json"

    def load(self) -> tuple[dict[str, Any], str | None]:
        if not self.path.exists():
            return {}, None
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            return {}, f"Saved data could not be read. New changes may replace it. ({error})"
        if not isinstance(data, dict):
            return {}, "Saved data is not a valid JSON object. New changes may replace it."
        return data, None

    def save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                json.dump(data, temporary_file, ensure_ascii=False, indent=2)
                temporary_file.write("\n")
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, self.path)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()
