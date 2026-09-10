from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date

from app.database.connection import Database

VALID_STATUSES = frozenset(
    {"DAY_OFF", "VACATION", "MEDICAL_LEAVE", "ABSENCE", "WORK_OVERRIDE"}
)
VALID_SOURCES = frozenset({"MANUAL", "DEFAULT", "LEAVE"})


@dataclass(frozen=True, slots=True)
class ScheduleEntry:
    employee_id: int
    date: date
    status: str
    notes: str | None = None
    source: str = "MANUAL"
    leave_period_id: int | None = None


class ScheduleRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def list_month(self, year: int, month: int) -> list[ScheduleEntry]:
        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])
        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT employee_id, date, status, notes, source, leave_period_id
                FROM schedule_entries
                WHERE date BETWEEN ? AND ?
                ORDER BY employee_id, date
                """,
                (start.isoformat(), end.isoformat()),
            ).fetchall()
        return [
            ScheduleEntry(
                employee_id=row["employee_id"],
                date=date.fromisoformat(row["date"]),
                status=row["status"],
                notes=row["notes"],
                source=row["source"],
                leave_period_id=row["leave_period_id"],
            )
            for row in rows
        ]

    def set_status(
        self,
        employee_id: int,
        entry_date: date,
        status: str | None,
        notes: str | None = None,
        source: str = "MANUAL",
    ) -> None:
        with self.database.transaction() as connection:
            current = connection.execute(
                """
                SELECT source FROM schedule_entries
                WHERE employee_id = ? AND date = ?
                """,
                (employee_id, entry_date.isoformat()),
            ).fetchone()
            if current is not None and current["source"] == "LEAVE":
                raise ValueError(
                    "Esta data pertence a um afastamento. Use a aba Afastamentos."
                )
            if status is None:
                connection.execute(
                    "DELETE FROM schedule_entries WHERE employee_id = ? AND date = ?",
                    (employee_id, entry_date.isoformat()),
                )
                return
            if status not in VALID_STATUSES:
                raise ValueError("Status de escala inválido.")
            if source not in VALID_SOURCES:
                raise ValueError("Origem de escala inválida.")
            if source == "LEAVE":
                raise ValueError("Use o serviço de afastamentos para essa origem.")
            connection.execute(
                """
                INSERT INTO schedule_entries(
                    employee_id, date, status, source, notes, leave_period_id
                )
                VALUES (?, ?, ?, ?, ?, NULL)
                ON CONFLICT(employee_id, date)
                DO UPDATE SET
                    status = excluded.status,
                    source = excluded.source,
                    notes = excluded.notes,
                    leave_period_id = NULL
                """,
                (employee_id, entry_date.isoformat(), status, source, notes),
            )

    def add_default_entries(self, entries: list[ScheduleEntry]) -> None:
        if not entries:
            return
        with self.database.transaction() as connection:
            connection.executemany(
                """
                INSERT OR IGNORE INTO schedule_entries(
                    employee_id, date, status, source, notes, leave_period_id
                )
                VALUES (?, ?, 'DAY_OFF', 'DEFAULT', NULL, NULL)
                """,
                ((entry.employee_id, entry.date.isoformat()) for entry in entries),
            )

    def set_day_off_employees(
        self, entry_date: date, selected_employee_ids: set[int]
    ) -> set[int]:
        """Apply manual choices without overriding vacation, leave or absence."""
        date_text = entry_date.isoformat()
        with self.database.transaction() as connection:
            rows = connection.execute(
                """
                SELECT
                    employees.id AS employee_id,
                    employees.default_day_off,
                    schedule_entries.status,
                    schedule_entries.source
                FROM employees
                LEFT JOIN schedule_entries
                  ON schedule_entries.employee_id = employees.id
                 AND schedule_entries.date = ?
                """,
                (date_text,),
            ).fetchall()
            blocked_ids: set[int] = set()
            ids_to_delete: list[int] = []
            ids_to_override: list[int] = []
            ids_to_restore: list[int] = []
            ids_to_add: list[int] = []
            weekday = entry_date.weekday()

            for row in rows:
                employee_id = int(row["employee_id"])
                status = row["status"]
                follows_default = row["default_day_off"] == weekday
                if employee_id in selected_employee_ids:
                    if status is None:
                        ids_to_add.append(employee_id)
                    elif status == "WORK_OVERRIDE":
                        ids_to_restore.append(employee_id)
                    elif status not in {"DAY_OFF"}:
                        blocked_ids.add(employee_id)
                elif status == "DAY_OFF":
                    if follows_default:
                        ids_to_override.append(employee_id)
                    else:
                        ids_to_delete.append(employee_id)
                elif status is None and follows_default:
                    ids_to_override.append(employee_id)

            connection.executemany(
                """
                DELETE FROM schedule_entries
                WHERE employee_id = ? AND date = ? AND status = 'DAY_OFF'
                """,
                ((employee_id, date_text) for employee_id in ids_to_delete),
            )
            connection.executemany(
                """
                INSERT INTO schedule_entries(employee_id, date, status, source, notes)
                VALUES (?, ?, 'WORK_OVERRIDE', 'MANUAL', NULL)
                ON CONFLICT(employee_id, date) DO UPDATE SET
                    status = 'WORK_OVERRIDE', source = 'MANUAL', notes = NULL,
                    leave_period_id = NULL
                """,
                ((employee_id, date_text) for employee_id in ids_to_override),
            )
            connection.executemany(
                """
                UPDATE schedule_entries
                SET status = 'DAY_OFF', source = 'MANUAL', notes = NULL,
                    leave_period_id = NULL
                WHERE employee_id = ? AND date = ? AND status = 'WORK_OVERRIDE'
                """,
                ((employee_id, date_text) for employee_id in ids_to_restore),
            )
            connection.executemany(
                """
                INSERT INTO schedule_entries(employee_id, date, status, source, notes)
                VALUES (?, ?, 'DAY_OFF', 'MANUAL', NULL)
                """,
                ((employee_id, date_text) for employee_id in ids_to_add),
            )
        return blocked_ids

    def replace_with_previous_month(self, year: int, month: int) -> int:
        target_start = date(year, month, 1)
        if month == 1:
            source_year, source_month = year - 1, 12
        else:
            source_year, source_month = year, month - 1
        source_start = date(source_year, source_month, 1)
        source_end = date(
            source_year,
            source_month,
            calendar.monthrange(source_year, source_month)[1],
        )
        target_days = calendar.monthrange(year, month)[1]

        with self.database.transaction() as connection:
            source_rows = connection.execute(
                """
                SELECT employee_id, date, status, notes, source
                FROM schedule_entries
                WHERE date BETWEEN ? AND ?
                  AND source = 'MANUAL'
                  AND status != 'WORK_OVERRIDE'
                """,
                (source_start.isoformat(), source_end.isoformat()),
            ).fetchall()
            target_end = date(year, month, target_days)
            connection.execute(
                """
                DELETE FROM schedule_entries
                WHERE date BETWEEN ? AND ? AND source != 'LEAVE'
                """,
                (target_start.isoformat(), target_end.isoformat()),
            )
            copied = 0
            for row in source_rows:
                source_date = date.fromisoformat(row["date"])
                if source_date.day > target_days:
                    continue
                target_date = date(year, month, source_date.day)
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO schedule_entries(
                        employee_id, date, status, source, notes, leave_period_id
                    )
                    VALUES (?, ?, ?, 'MANUAL', ?, NULL)
                    """,
                    (
                        row["employee_id"],
                        target_date.isoformat(),
                        row["status"],
                        row["notes"],
                    ),
                )
                copied += cursor.rowcount
        return copied
