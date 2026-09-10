from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date

from app.database.connection import Database


@dataclass(frozen=True, slots=True)
class Employee:
    id: int
    name: str
    default_day_off: int | None = None


class EmployeeRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def list_all(self) -> list[Employee]:
        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT id, name, default_day_off
                FROM employees
                ORDER BY name COLLATE NOCASE
                """
            ).fetchall()
        return [
            Employee(
                id=row["id"],
                name=row["name"],
                default_day_off=row["default_day_off"],
            )
            for row in rows
        ]

    def add(self, name: str, default_day_off: int | None) -> Employee:
        with self.database.transaction() as connection:
            cursor = connection.execute(
                "INSERT INTO employees(name, default_day_off) VALUES (?, ?)",
                (name, default_day_off),
            )
            employee_id = int(cursor.lastrowid)
        return Employee(employee_id, name, default_day_off)

    def update(
        self,
        employee_id: int,
        name: str,
        default_day_off: int | None,
        future_from: date,
    ) -> None:
        with self.database.transaction() as connection:
            current = connection.execute(
                "SELECT default_day_off FROM employees WHERE id = ?",
                (employee_id,),
            ).fetchone()
            if current is None:
                raise LookupError("Funcionário não encontrado.")
            cursor = connection.execute(
                """
                UPDATE employees
                SET name = ?, default_day_off = ?
                WHERE id = ?
                """,
                (name, default_day_off, employee_id),
            )
            if cursor.rowcount == 0:
                raise LookupError("Funcionário não encontrado.")
            if current["default_day_off"] != default_day_off:
                connection.execute(
                    """
                    DELETE FROM schedule_entries
                    WHERE employee_id = ?
                      AND date >= ?
                      AND status = 'DAY_OFF'
                      AND source = 'DEFAULT'
                    """,
                    (employee_id, future_from.isoformat()),
                )

    def delete(self, employee_id: int) -> None:
        try:
            with self.database.transaction() as connection:
                cursor = connection.execute(
                    "DELETE FROM employees WHERE id = ?", (employee_id,)
                )
                if cursor.rowcount == 0:
                    raise LookupError("Funcionário não encontrado.")
        except sqlite3.IntegrityError as error:
            raise EmployeeHasScheduleError(
                "Este funcionário possui afastamentos ou registros de escala e não "
                "pode ser excluído."
            ) from error


class EmployeeHasScheduleError(ValueError):
    pass
