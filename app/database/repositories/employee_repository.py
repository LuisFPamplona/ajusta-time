from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from app.database.connection import Database


@dataclass(frozen=True, slots=True)
class Employee:
    id: int
    name: str


class EmployeeRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def list_all(self) -> list[Employee]:
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT id, name FROM employees ORDER BY name COLLATE NOCASE"
            ).fetchall()
        return [Employee(id=row["id"], name=row["name"]) for row in rows]

    def add(self, name: str) -> Employee:
        with self.database.transaction() as connection:
            cursor = connection.execute(
                "INSERT INTO employees(name) VALUES (?)", (name,)
            )
            employee_id = int(cursor.lastrowid)
        return Employee(employee_id, name)

    def update(self, employee_id: int, name: str) -> None:
        with self.database.transaction() as connection:
            cursor = connection.execute(
                "UPDATE employees SET name = ? WHERE id = ?",
                (name, employee_id),
            )
            if cursor.rowcount == 0:
                raise LookupError("Funcionário não encontrado.")

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
                "Este funcionário possui registros de escala e não pode ser excluído."
            ) from error


class EmployeeHasScheduleError(ValueError):
    pass
