from __future__ import annotations

from app.database.repositories.employee_repository import Employee, EmployeeRepository


class EmployeeService:
    def __init__(self, repository: EmployeeRepository) -> None:
        self.repository = repository

    def list_employees(self) -> list[Employee]:
        return self.repository.list_all()

    def add_employee(self, name: str) -> Employee:
        return self.repository.add(self._validate_name(name))

    def update_employee(self, employee_id: int, name: str) -> None:
        self.repository.update(employee_id, self._validate_name(name))

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
