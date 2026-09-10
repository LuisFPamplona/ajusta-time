from __future__ import annotations

from app.database.connection import Database
from app.database.repositories.settings_repository import DEFAULT_SETTINGS

BASE_SCHEMA = """
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    default_day_off INTEGER CHECK (
        default_day_off IS NULL OR default_day_off BETWEEN 0 AND 6
    )
);

CREATE TABLE IF NOT EXISTS leave_periods (
    id INTEGER PRIMARY KEY,
    employee_id INTEGER NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('VACATION', 'MEDICAL_LEAVE')),
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    notes TEXT,
    CHECK (start_date <= end_date),
    FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS schedule_entries (
    id INTEGER PRIMARY KEY,
    employee_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    status TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'MANUAL'
        CHECK (source IN ('MANUAL', 'DEFAULT', 'LEAVE')),
    notes TEXT,
    leave_period_id INTEGER,
    UNIQUE(employee_id, date),
    FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE RESTRICT,
    FOREIGN KEY(leave_period_id) REFERENCES leave_periods(id) ON DELETE RESTRICT,
    CHECK (
        (
            source = 'LEAVE'
            AND leave_period_id IS NOT NULL
            AND status IN ('VACATION', 'MEDICAL_LEAVE')
        ) OR
        (source != 'LEAVE' AND leave_period_id IS NULL)
    ),
    CHECK (source != 'DEFAULT' OR status = 'DAY_OFF')
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""

EXAMPLE_EMPLOYEES = ("João Silva", "Maria Souza", "Carlos Lima")


def initialize_database(database: Database) -> None:
    with database.transaction() as connection:
        connection.executescript(BASE_SCHEMA)
        employee_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(employees)")
        }
        if "default_day_off" not in employee_columns:
            connection.execute(
                """
                ALTER TABLE employees
                ADD COLUMN default_day_off INTEGER CHECK (
                    default_day_off IS NULL OR default_day_off BETWEEN 0 AND 6
                )
                """
            )
        schedule_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(schedule_entries)")
        }
        if "source" not in schedule_columns:
            connection.execute(
                """
                ALTER TABLE schedule_entries
                ADD COLUMN source TEXT NOT NULL DEFAULT 'MANUAL'
                CHECK (source IN ('MANUAL', 'DEFAULT'))
                """
            )
        if "leave_period_id" not in schedule_columns:
            connection.execute(
                "ALTER TABLE schedule_entries RENAME TO schedule_entries_legacy"
            )
            connection.execute(
                """
                CREATE TABLE schedule_entries (
                    id INTEGER PRIMARY KEY,
                    employee_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    status TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT 'MANUAL'
                        CHECK (source IN ('MANUAL', 'DEFAULT', 'LEAVE')),
                    notes TEXT,
                    leave_period_id INTEGER,
                    UNIQUE(employee_id, date),
                    FOREIGN KEY(employee_id) REFERENCES employees(id)
                        ON DELETE RESTRICT,
                    FOREIGN KEY(leave_period_id) REFERENCES leave_periods(id)
                        ON DELETE RESTRICT,
                    CHECK (
                        (
                            source = 'LEAVE'
                            AND leave_period_id IS NOT NULL
                            AND status IN ('VACATION', 'MEDICAL_LEAVE')
                        ) OR
                        (source != 'LEAVE' AND leave_period_id IS NULL)
                    ),
                    CHECK (source != 'DEFAULT' OR status = 'DAY_OFF')
                )
                """
            )
            connection.execute(
                """
                INSERT INTO schedule_entries(
                    id, employee_id, date, status, source, notes, leave_period_id
                )
                SELECT id, employee_id, date, status, source, notes, NULL
                FROM schedule_entries_legacy
                """
            )
            connection.execute("DROP TABLE schedule_entries_legacy")
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_leave_periods_employee_dates
            ON leave_periods(employee_id, start_date, end_date)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_schedule_entries_leave_period
            ON schedule_entries(leave_period_id)
            """
        )
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
