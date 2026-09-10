from __future__ import annotations

from app.database.connection import Database
from app.database.repositories.settings_repository import DEFAULT_SETTINGS

EMPLOYEES_SCHEMA = """
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    default_day_off INTEGER CHECK (
        default_day_off IS NULL OR default_day_off BETWEEN 0 AND 6
    )
)
"""

LEAVE_PERIODS_SCHEMA = """
CREATE TABLE IF NOT EXISTS leave_periods (
    id INTEGER PRIMARY KEY,
    employee_id INTEGER NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('VACATION', 'MEDICAL_LEAVE')),
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    notes TEXT,
    CHECK (start_date <= end_date),
    FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE RESTRICT
)
"""

SETTINGS_SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
"""

EXAMPLE_EMPLOYEES = ("João Silva", "Maria Souza", "Carlos Lima")


def initialize_database(database: Database) -> None:
    with database.transaction() as connection:
        connection.execute(EMPLOYEES_SCHEMA)
        connection.execute(LEAVE_PERIODS_SCHEMA)
        connection.execute(SETTINGS_SCHEMA)
        schedule_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = ? AND name = ?",
            ("table", "schedule_entries"),
        ).fetchone()
        if schedule_exists is None:
            connection.execute(_schedule_table_schema("schedule_entries"))

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
        schedule_columns = _column_names(connection, "schedule_entries")
        if "source" not in schedule_columns:
            connection.execute(
                """
                ALTER TABLE schedule_entries
                ADD COLUMN source TEXT NOT NULL DEFAULT 'MANUAL'
                CHECK (source IN ('MANUAL', 'DEFAULT'))
                """
            )
            schedule_columns.add("source")
        schedule_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = ? AND name = ?",
            ("table", "schedule_entries"),
        ).fetchone()["sql"]
        if (
            "leave_period_id" not in schedule_columns
            or "'LEAVE'" not in schedule_sql
            or "source != 'DEFAULT'" not in schedule_sql
        ):
            _rebuild_schedule_entries(connection, schedule_columns)
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
        connection.execute("PRAGMA user_version = 2")
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


def _schedule_table_schema(table_name: str) -> str:
    if table_name not in {"schedule_entries", "schedule_entries_new"}:
        raise ValueError("Nome interno de tabela inválido.")
    return f"""
        CREATE TABLE {table_name} (
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


def _column_names(connection, table_name: str) -> set[str]:
    if table_name != "schedule_entries":
        raise ValueError("Nome interno de tabela inválido.")
    return {
        row["name"] for row in connection.execute(f"PRAGMA table_info({table_name})")
    }


def _rebuild_schedule_entries(connection, columns: set[str]) -> None:
    connection.execute(_schedule_table_schema("schedule_entries_new"))
    leave_period_expression = (
        "leave_period_id" if "leave_period_id" in columns else "NULL"
    )
    connection.execute(
        f"""
        INSERT INTO schedule_entries_new(
            id, employee_id, date, status, source, notes, leave_period_id
        )
        SELECT
            id, employee_id, date, status, source, notes,
            {leave_period_expression}
        FROM schedule_entries
        """
    )
    old_count = connection.execute("SELECT COUNT(*) FROM schedule_entries").fetchone()[
        0
    ]
    new_count = connection.execute(
        "SELECT COUNT(*) FROM schedule_entries_new"
    ).fetchone()[0]
    if old_count != new_count:
        raise RuntimeError("A migração não preservou todas as ocorrências da escala.")
    if connection.execute("PRAGMA foreign_key_check(schedule_entries_new)").fetchone():
        raise RuntimeError("A migração encontrou vínculos inválidos na escala.")
    connection.execute("DROP TABLE schedule_entries")
    connection.execute("ALTER TABLE schedule_entries_new RENAME TO schedule_entries")
