from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date

from app.database.connection import Database

VALID_STATUSES = frozenset({"DAY_OFF", "VACATION", "MEDICAL_LEAVE", "ABSENCE"})


@dataclass(frozen=True, slots=True)
class ScheduleEntry:
    employee_id: int
    date: date
    status: str
    notes: str | None = None


class ScheduleRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def list_month(self, year: int, month: int) -> list[ScheduleEntry]:
        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])
        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT employee_id, date, status, notes
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
            )
            for row in rows
        ]

    def set_status(
        self,
        employee_id: int,
        entry_date: date,
        status: str | None,
        notes: str | None = None,
    ) -> None:
        with self.database.transaction() as connection:
            if status is None:
                connection.execute(
                    "DELETE FROM schedule_entries WHERE employee_id = ? AND date = ?",
                    (employee_id, entry_date.isoformat()),
                )
                return
            if status not in VALID_STATUSES:
                raise ValueError("Status de escala inválido.")
            connection.execute(
                """
                INSERT INTO schedule_entries(employee_id, date, status, notes)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(employee_id, date)
                DO UPDATE SET status = excluded.status, notes = excluded.notes
                """,
                (employee_id, entry_date.isoformat(), status, notes),
            )

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
                SELECT employee_id, date, status, notes
                FROM schedule_entries
                WHERE date BETWEEN ? AND ?
                """,
                (source_start.isoformat(), source_end.isoformat()),
            ).fetchall()
            target_end = date(year, month, target_days)
            connection.execute(
                "DELETE FROM schedule_entries WHERE date BETWEEN ? AND ?",
                (target_start.isoformat(), target_end.isoformat()),
            )
            copied = 0
            for row in source_rows:
                source_date = date.fromisoformat(row["date"])
                if source_date.day > target_days:
                    continue
                target_date = date(year, month, source_date.day)
                connection.execute(
                    """
                    INSERT INTO schedule_entries(employee_id, date, status, notes)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        row["employee_id"],
                        target_date.isoformat(),
                        row["status"],
                        row["notes"],
                    ),
                )
                copied += 1
        return copied
