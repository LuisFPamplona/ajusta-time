from __future__ import annotations

from datetime import date

from app.database.repositories.schedule_repository import (
    VALID_STATUSES,
    ScheduleEntry,
    ScheduleRepository,
)

STATUS_LABELS = {
    "DAY_OFF": "F",
    "VACATION": "FE",
    "MEDICAL_LEAVE": "AT",
    "ABSENCE": "FA",
}

STATUS_NAMES = {
    "DAY_OFF": "Folga",
    "VACATION": "Férias",
    "MEDICAL_LEAVE": "Atestado",
    "ABSENCE": "Falta",
}


class ScheduleService:
    def __init__(self, repository: ScheduleRepository) -> None:
        self.repository = repository

    def month_entries(self, year: int, month: int) -> dict[tuple[int, int], str]:
        return {
            (entry.employee_id, entry.date.day): entry.status
            for entry in self.repository.list_month(year, month)
        }

    def month_entry_list(self, year: int, month: int) -> list[ScheduleEntry]:
        return self.repository.list_month(year, month)

    def set_status(
        self, employee_id: int, year: int, month: int, day: int, status: str | None
    ) -> None:
        if status is not None and status not in VALID_STATUSES:
            raise ValueError("Status de escala inválido.")
        self.repository.set_status(employee_id, date(year, month, day), status)

    def copy_previous_month(self, year: int, month: int) -> int:
        return self.repository.replace_with_previous_month(year, month)
