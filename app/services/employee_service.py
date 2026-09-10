from __future__ import annotations

from datetime import date, datetime

from app.database.repositories.employee_repository import Employee, EmployeeRepository


class EmployeeService:
    def __init__(self, repository: EmployeeRepository) -> None:
        self.repository = repository

    def list_employees(self) -> list[Employee]:
        return self.repository.list_all()

    def add_employee(self, name: str, default_day_off: int | None = None) -> Employee:
        return self.repository.add(
            self._validate_name(name), self._validate_default_day_off(default_day_off)
        )

    def update_employee(
        self,
        employee_id: int,
        name: str,
        default_day_off: int | None = None,
        today: date | None = None,
    ) -> None:
        effective_today = today or datetime.now().astimezone().date()
        self.repository.update(
            employee_id,
            self._validate_name(name),
            self._validate_default_day_off(default_day_off),
            effective_today,
        )

    def delete_employee(self, employee_id: int) -> None:
        self.repository.delete(employee_id)

    @staticmethod
    def _validate_name(name: str) -> str:
        normalized = " ".join(name.split())
        if not normalized:
            raise ValueError("Informe o nome do funcionário.")
        if len(normalized) > 150:
            raise ValueError("O nome deve ter no máximo 150 caracteres.")
        return normalized

    @staticmethod
    def _validate_default_day_off(value: int | None) -> int | None:
        if value is not None and (
            not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 6
        ):
            raise ValueError("A folga padrão deve ser um dia válido da semana.")
        return value
