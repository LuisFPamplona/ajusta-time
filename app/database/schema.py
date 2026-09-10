from __future__ import annotations

from app.database.connection import Database
from app.database.repositories.settings_repository import DEFAULT_SETTINGS

SCHEMA = """
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS schedule_entries (
    id INTEGER PRIMARY KEY,
    employee_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    status TEXT NOT NULL,
    notes TEXT,
    UNIQUE(employee_id, date),
    FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""

EXAMPLE_EMPLOYEES = ("João Silva", "Maria Souza", "Carlos Lima")


def initialize_database(database: Database) -> None:
    with database.transaction() as connection:
        connection.executescript(SCHEMA)
        connection.executemany(
            "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)",
            DEFAULT_SETTINGS.items(),
        )
        initialized = connection.execute(
            "SELECT value FROM settings WHERE key = ?",
            ("demo_data_initialized",),
        ).fetchone()
        if initialized is None:
            employee_count = connection.execute(
                "SELECT COUNT(*) FROM employees"
            ).fetchone()[0]
            if employee_count == 0:
                connection.executemany(
                    "INSERT INTO employees(name) VALUES (?)",
                    ((name,) for name in EXAMPLE_EMPLOYEES),
                )
            connection.execute(
                "INSERT INTO settings(key, value) VALUES (?, ?)",
                ("demo_data_initialized", "1"),
            )
