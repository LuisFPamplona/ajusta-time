from __future__ import annotations

import logging
import os
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

from app.database.connection import Database

DATA_DIR_ENV = "AJUSTA_TIME_DATA_DIR"
_REQUIRED_LEGACY_TABLES = frozenset({"employees", "schedule_entries", "settings"})


def project_root() -> Path:
    """Return the application resource root without relying on the current folder."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def get_app_data_dir() -> Path:
    """Return and create the per-user writable data directory."""
    override = os.environ.get(DATA_DIR_ENV)
    if override:
        base = Path(override).expanduser()
    elif sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        base = (
            Path(local_app_data)
            if local_app_data
            else Path.home() / "AppData" / "Local"
        ) / "AjustaTime"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "AjustaTime"
    else:
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        base = (
            Path(xdg_data_home).expanduser()
            if xdg_data_home
            else Path.home() / ".local" / "share"
        ) / "AjustaTime"
    base.mkdir(parents=True, exist_ok=True)
    return base.resolve()


def get_database_path() -> Path:
    return get_app_data_dir() / "escala.db"


def get_log_dir() -> Path:
    directory = get_app_data_dir() / "logs"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def get_legacy_database_path() -> Path:
    return project_root() / "data" / "escala.db"


def migrate_legacy_database(destination: Path, legacy: Path | None = None) -> bool:
    """Copy a valid legacy database once, never overwriting the destination."""
    source = (legacy or get_legacy_database_path()).resolve()
    destination = destination.resolve()
    if destination.exists() or source == destination or not source.is_file():
        return False
    if not _is_valid_legacy_database(source):
        logging.getLogger("ajusta_time.paths").warning(
            "Banco legado ignorado porque não passou na validação de integridade."
        )
        return False

    Database(source).backup_to(destination)
    logging.getLogger("ajusta_time.paths").info(
        "Banco legado migrado com segurança para o diretório de dados do usuário."
    )
    return True


def _is_valid_legacy_database(path: Path) -> bool:
    try:
        with closing(sqlite3.connect(path)) as connection:
            integrity = connection.execute("PRAGMA quick_check").fetchone()
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = ?", ("table",)
                )
            }
    except sqlite3.Error:
        return False
    return (
        bool(integrity and integrity[0] == "ok") and _REQUIRED_LEGACY_TABLES <= tables
    )


# Backward-compatible aliases for existing integrations.
data_directory = get_app_data_dir
database_path = get_database_path
