from __future__ import annotations

import sys
from pathlib import Path


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def data_directory() -> Path:
    directory = project_root() / "data"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def database_path() -> Path:
    return data_directory() / "escala.db"
