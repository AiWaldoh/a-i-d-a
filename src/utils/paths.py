import os
from pathlib import Path

def get_project_root() -> Path:
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent
    return project_root

def get_absolute_path(relative_path: str) -> Path:
    project_root = get_project_root()
    return project_root / relative_path

