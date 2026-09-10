from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from app.database.connection import Database
from app.database.repositories.schedule_repository import ScheduleEntry

VALID_LEAVE_TYPES = frozenset({"VACATION", "MEDICAL_LEAVE"})


@dataclass(frozen=True, slots=True)
class LeavePeriod:
    id: int
    employee_id: int
    employee_name: str
    type: str
    start_date: date
    end_date: date
    notes: str | None = None

    @property
    def days(self) -> int:
        return (self.end_date - self.start_date).days + 1


class LeaveRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def list_all(
        self, employee_id: int | None = None, leave_type: str | None = None
    ) -> list[LeavePeriod]:
        clauses: list[str] = []
        parameters: list[object] = []
        if employee_id is not None:
            clauses.append("leave_periods.employee_id = ?")
            parameters.append(employee_id)
        if leave_type is not None:
            clauses.append("leave_periods.type = ?")
            parameters.append(leave_type)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self.database.connection() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    leave_periods.id,
                    leave_periods.employee_id,
                    employees.name AS employee_name,
                    leave_periods.type,
                    leave_periods.start_date,
                    leave_periods.end_date,
                    leave_periods.notes
                FROM leave_periods
                JOIN employees ON employees.id = leave_periods.employee_id
                {where}
                ORDER BY leave_periods.start_date, employees.name COLLATE NOCASE
                """,
                parameters,
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def get(self, leave_id: int) -> LeavePeriod:
        with self.database.connection() as connection:
            leave = self.get_with_connection(connection, leave_id)
        if leave is None:
            raise LookupError("Afastamento não encontrado.")
        return leave

    @classmethod
    def get_with_connection(
        cls, connection: sqlite3.Connection, leave_id: int
    ) -> LeavePeriod | None:
        row = connection.execute(
            """
            SELECT
                leave_periods.id,
                leave_periods.employee_id,
                employees.name AS employee_name,
                leave_periods.type,
                leave_periods.start_date,
                leave_periods.end_date,
                leave_periods.notes
            FROM leave_periods
            JOIN employees ON employees.id = leave_periods.employee_id
            WHERE leave_periods.id = ?
            """,
            (leave_id,),
        ).fetchone()
        return cls._from_row(row) if row is not None else None

    @staticmethod
    def find_overlap(
        connection: sqlite3.Connection,
        employee_id: int,
        start_date: date,
        end_date: date,
        exclude_leave_id: int | None = None,
    ) -> sqlite3.Row | None:
        return connection.execute(
            """
            SELECT id, start_date, end_date
            FROM leave_periods
            WHERE employee_id = ?
              AND start_date <= ?
              AND end_date >= ?
              AND (? IS NULL OR id != ?)
            LIMIT 1
            """,
            (
                employee_id,
                end_date.isoformat(),
                start_date.isoformat(),
                exclude_leave_id,
                exclude_leave_id,
            ),
        ).fetchone()

    @staticmethod
    def list_conflicts(
        connection: sqlite3.Connection,
        employee_id: int,
        start_date: date,
        end_date: date,
        exclude_leave_id: int | None = None,
    ) -> list[ScheduleEntry]:
        rows = connection.execute(
            """
            SELECT employee_id, date, status, notes, source, leave_period_id
            FROM schedule_entries
            WHERE employee_id = ?
              AND date BETWEEN ? AND ?
              AND NOT (status = 'DAY_OFF' AND source = 'DEFAULT')
              AND (? IS NULL OR leave_period_id IS NULL OR leave_period_id != ?)
            ORDER BY date
            """,
            (
                employee_id,
                start_date.isoformat(),
                end_date.isoformat(),
                exclude_leave_id,
                exclude_leave_id,
            ),
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

    @staticmethod
    def employee_exists(connection: sqlite3.Connection, employee_id: int) -> bool:
        return (
            connection.execute(
                "SELECT 1 FROM employees WHERE id = ?", (employee_id,)
            ).fetchone()
            is not None
        )

    @staticmethod
    def insert(
        connection: sqlite3.Connection,
        employee_id: int,
        leave_type: str,
        start_date: date,
        end_date: date,
        notes: str | None,
    ) -> int:
        cursor = connection.execute(
            """
            INSERT INTO leave_periods(
                employee_id, type, start_date, end_date, notes
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                employee_id,
                leave_type,
                start_date.isoformat(),
                end_date.isoformat(),
                notes,
            ),
        )
        return int(cursor.lastrowid)

    @staticmethod
    def update(
        connection: sqlite3.Connection,
        leave_id: int,
        employee_id: int,
        leave_type: str,
        start_date: date,
        end_date: date,
        notes: str | None,
    ) -> None:
        cursor = connection.execute(
            """
            UPDATE leave_periods
            SET employee_id = ?, type = ?, start_date = ?, end_date = ?, notes = ?
            WHERE id = ?
            """,
            (
                employee_id,
                leave_type,
                start_date.isoformat(),
                end_date.isoformat(),
                notes,
                leave_id,
            ),
        )
        if cursor.rowcount == 0:
            raise LookupError("Afastamento não encontrado.")

    @staticmethod
    def delete(connection: sqlite3.Connection, leave_id: int) -> None:
        cursor = connection.execute(
            "DELETE FROM leave_periods WHERE id = ?", (leave_id,)
        )
        if cursor.rowcount == 0:
            raise LookupError("Afastamento não encontrado.")

    @staticmethod
    def delete_linked_entries(connection: sqlite3.Connection, leave_id: int) -> None:
        connection.execute(
            "DELETE FROM schedule_entries WHERE leave_period_id = ?", (leave_id,)
        )

    @staticmethod
    def replace_range_with_leave(
        connection: sqlite3.Connection,
        leave_id: int,
        employee_id: int,
        leave_type: str,
        start_date: date,
        end_date: date,
        notes: str | None,
        days: Iterable[date],
    ) -> None:
        connection.execute(
            """
            DELETE FROM schedule_entries
            WHERE employee_id = ? AND date BETWEEN ? AND ?
            """,
            (employee_id, start_date.isoformat(), end_date.isoformat()),
        )
        connection.executemany(
            """
            INSERT INTO schedule_entries(
                employee_id, date, status, source, notes, leave_period_id
            )
            VALUES (?, ?, ?, 'LEAVE', ?, ?)
            """,
            (
                (employee_id, day.isoformat(), leave_type, notes, leave_id)
                for day in days
            ),
        )

    @staticmethod
    def default_day_off(connection: sqlite3.Connection, employee_id: int) -> int | None:
        employee = connection.execute(
            "SELECT default_day_off FROM employees WHERE id = ?", (employee_id,)
        ).fetchone()
        if employee is None or employee["default_day_off"] is None:
            return None
        return int(employee["default_day_off"])

    @staticmethod
    def add_default_days(
        connection: sqlite3.Connection, employee_id: int, days: Iterable[date]
    ) -> None:
        connection.executemany(
            """
            INSERT OR IGNORE INTO schedule_entries(
                employee_id, date, status, source, notes, leave_period_id
            )
            VALUES (?, ?, 'DAY_OFF', 'DEFAULT', NULL, NULL)
            """,
            ((employee_id, day.isoformat()) for day in days),
        )

    @staticmethod
    def _from_row(row: sqlite3.Row) -> LeavePeriod:
        return LeavePeriod(
            id=row["id"],
            employee_id=row["employee_id"],
            employee_name=row["employee_name"],
            type=row["type"],
            start_date=date.fromisoformat(row["start_date"]),
            end_date=date.fromisoformat(row["end_date"]),
            notes=row["notes"],
        )
