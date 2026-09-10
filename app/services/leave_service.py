from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from app.database.repositories.leave_repository import (
    VALID_LEAVE_TYPES,
    LeavePeriod,
    LeaveRepository,
)
from app.database.repositories.schedule_repository import ScheduleEntry

LEAVE_TYPE_NAMES = {
    "VACATION": "Férias",
    "MEDICAL_LEAVE": "Atestado",
}


class LeaveOverlapError(ValueError):
    pass


class LeaveConflictError(ValueError):
    def __init__(self, conflicts: list[ScheduleEntry]) -> None:
        super().__init__("Existem ocorrências já cadastradas nesse período.")
        self.conflicts = conflicts


class LeaveService:
    def __init__(self, repository: LeaveRepository) -> None:
        self.repository = repository

    def list_leaves(
        self, employee_id: int | None = None, leave_type: str | None = None
    ) -> list[LeavePeriod]:
        if leave_type is not None and leave_type not in VALID_LEAVE_TYPES:
            raise ValueError("Tipo de afastamento inválido.")
        return self.repository.list_all(employee_id, leave_type)

    def get_leave(self, leave_id: int) -> LeavePeriod:
        return self.repository.get(leave_id)

    def create_leave(
        self,
        employee_id: int,
        leave_type: str,
        start_date: date,
        end_date: date,
        notes: str = "",
        replace_conflicts: bool = False,
    ) -> LeavePeriod:
        normalized_notes = self._validate(
            employee_id, leave_type, start_date, end_date, notes
        )
        with self.repository.database.transaction() as connection:
            self._ensure_employee(connection, employee_id)
            self._ensure_no_overlap(connection, employee_id, start_date, end_date)
            conflicts = self.repository.list_conflicts(
                connection, employee_id, start_date, end_date
            )
            if conflicts and not replace_conflicts:
                raise LeaveConflictError(conflicts)
            leave_id = self.repository.insert(
                connection,
                employee_id,
                leave_type,
                start_date,
                end_date,
                normalized_notes,
            )
            self._replace_range_with_leave(
                connection,
                leave_id,
                employee_id,
                leave_type,
                start_date,
                end_date,
                normalized_notes,
            )
        return self.repository.get(leave_id)

    def update_leave(
        self,
        leave_id: int,
        employee_id: int,
        leave_type: str,
        start_date: date,
        end_date: date,
        notes: str = "",
        replace_conflicts: bool = False,
    ) -> LeavePeriod:
        normalized_notes = self._validate(
            employee_id, leave_type, start_date, end_date, notes
        )
        with self.repository.database.transaction() as connection:
            old_leave = self.repository.get_with_connection(connection, leave_id)
            if old_leave is None:
                raise LookupError("Afastamento não encontrado.")
            self._ensure_employee(connection, employee_id)
            self._ensure_no_overlap(
                connection, employee_id, start_date, end_date, leave_id
            )
            conflicts = self.repository.list_conflicts(
                connection, employee_id, start_date, end_date, leave_id
            )
            if conflicts and not replace_conflicts:
                raise LeaveConflictError(conflicts)

            self.repository.delete_linked_entries(connection, leave_id)
            self.repository.update(
                connection,
                leave_id,
                employee_id,
                leave_type,
                start_date,
                end_date,
                normalized_notes,
            )
            self._replace_range_with_leave(
                connection,
                leave_id,
                employee_id,
                leave_type,
                start_date,
                end_date,
                normalized_notes,
            )
            self._restore_defaults(
                connection,
                old_leave.employee_id,
                old_leave.start_date,
                old_leave.end_date,
            )
        return self.repository.get(leave_id)

    def delete_leave(self, leave_id: int) -> None:
        with self.repository.database.transaction() as connection:
            leave = self.repository.get_with_connection(connection, leave_id)
            if leave is None:
                raise LookupError("Afastamento não encontrado.")
            self.repository.delete_linked_entries(connection, leave_id)
            self.repository.delete(connection, leave_id)
            self._restore_defaults(
                connection, leave.employee_id, leave.start_date, leave.end_date
            )

    @staticmethod
    def _validate(
        employee_id: int,
        leave_type: str,
        start_date: date,
        end_date: date,
        notes: str,
    ) -> str | None:
        if not isinstance(employee_id, int) or isinstance(employee_id, bool):
            raise TypeError("Funcionário inválido.")
        if employee_id <= 0:
            raise ValueError("Funcionário inválido.")
        if leave_type not in VALID_LEAVE_TYPES:
            raise ValueError("Tipo de afastamento inválido.")
        if not isinstance(start_date, date) or not isinstance(end_date, date):
            raise TypeError("Informe datas válidas.")
        if start_date > end_date:
            raise ValueError("A data inicial não pode ser posterior à data final.")
        normalized = " ".join(notes.split())
        if len(normalized) > 500:
            raise ValueError("A observação deve ter no máximo 500 caracteres.")
        return normalized or None

    def _ensure_employee(
        self, connection: sqlite3.Connection, employee_id: int
    ) -> None:
        if not self.repository.employee_exists(connection, employee_id):
            raise LookupError("Funcionário não encontrado.")

    def _ensure_no_overlap(
        self,
        connection: sqlite3.Connection,
        employee_id: int,
        start_date: date,
        end_date: date,
        exclude_leave_id: int | None = None,
    ) -> None:
        if self.repository.find_overlap(
            connection, employee_id, start_date, end_date, exclude_leave_id
        ):
            raise LeaveOverlapError(
                "Este funcionário já possui um afastamento nesse período."
            )

    def _replace_range_with_leave(
        self,
        connection: sqlite3.Connection,
        leave_id: int,
        employee_id: int,
        leave_type: str,
        start_date: date,
        end_date: date,
        notes: str | None,
    ) -> None:
        self.repository.replace_range_with_leave(
            connection,
            leave_id,
            employee_id,
            leave_type,
            start_date,
            end_date,
            notes,
            self._date_range(start_date, end_date),
        )

    def _restore_defaults(
        self,
        connection: sqlite3.Connection,
        employee_id: int,
        start_date: date,
        end_date: date,
    ) -> None:
        weekday = self.repository.default_day_off(connection, employee_id)
        if weekday is None:
            return
        self.repository.add_default_days(
            connection,
            employee_id,
            (
                day
                for day in self._date_range(start_date, end_date)
                if day.weekday() == weekday
            ),
        )

    @staticmethod
    def _date_range(start_date: date, end_date: date):
        for offset in range((end_date - start_date).days + 1):
            yield start_date + timedelta(days=offset)
