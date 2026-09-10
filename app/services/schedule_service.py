from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime

from app.database.repositories.employee_repository import Employee
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
    "WORK_OVERRIDE": "",
}

STATUS_NAMES = {
    "DAY_OFF": "Folga",
    "VACATION": "Férias",
    "MEDICAL_LEAVE": "Atestado",
    "ABSENCE": "Falta",
    "WORK_OVERRIDE": "Trabalho normal",
}

NOT_WORKING_STATUSES = frozenset(
    {"DAY_OFF", "VACATION", "MEDICAL_LEAVE", "ABSENCE"}
)


@dataclass(frozen=True, slots=True)
class DailyScheduleSummary:
    working: int
    day_off: int
    vacation: int
    medical_leave: int
    absence: int

    @property
    def unavailable(self) -> int:
        return self.day_off + self.vacation + self.medical_leave + self.absence


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

    def get_month_schedule(
        self,
        year: int,
        month: int,
        employees: list[Employee],
        today: date | None = None,
    ) -> list[ScheduleEntry]:
        entries = self.repository.list_month(year, month)
        effective_today = today or datetime.now().astimezone().date()
        month_start = date(year, month, 1)
        month_end = date(year, month, calendar.monthrange(year, month)[1])
        if month_end < effective_today:
            return entries

        existing_keys = {(entry.employee_id, entry.date) for entry in entries}
        historical_default_ids = {
            entry.employee_id
            for entry in entries
            if entry.status == "DAY_OFF"
            and entry.source == "DEFAULT"
            and entry.date < effective_today
        }
        generated: list[ScheduleEntry] = []
        for employee in employees:
            if employee.default_day_off is None:
                continue
            generation_start = month_start
            if (
                month_start <= effective_today <= month_end
                and employee.id in historical_default_ids
            ):
                generation_start = effective_today
            for day in range(1, month_end.day + 1):
                entry_date = date(year, month, day)
                key = (employee.id, entry_date)
                if (
                    entry_date >= generation_start
                    and entry_date.weekday() == employee.default_day_off
                    and key not in existing_keys
                ):
                    entry = ScheduleEntry(
                        employee_id=employee.id,
                        date=entry_date,
                        status="DAY_OFF",
                        source="DEFAULT",
                    )
                    generated.append(entry)
                    existing_keys.add(key)

        self.repository.add_default_entries(generated)
        return sorted(
            [*entries, *generated], key=lambda entry: (entry.employee_id, entry.date)
        )

    def get_month_daily_summary(
        self,
        year: int,
        month: int,
        employees: list[Employee],
        entries: list[ScheduleEntry] | None = None,
    ) -> dict[int, DailyScheduleSummary]:
        entry_list = (
            entries
            if entries is not None
            else self.get_month_schedule(year, month, employees)
        )
        employee_ids = {employee.id for employee in employees}
        statuses_by_day: dict[int, dict[int, str]] = {}
        for entry in entry_list:
            if (
                entry.employee_id in employee_ids
                and entry.date.year == year
                and entry.date.month == month
            ):
                statuses_by_day.setdefault(entry.date.day, {})[entry.employee_id] = (
                    entry.status
                )

        total_employees = len(employee_ids)
        summaries: dict[int, DailyScheduleSummary] = {}
        for day in range(1, calendar.monthrange(year, month)[1] + 1):
            statuses = statuses_by_day.get(day, {}).values()
            day_off = sum(status == "DAY_OFF" for status in statuses)
            vacation = sum(status == "VACATION" for status in statuses)
            medical_leave = sum(status == "MEDICAL_LEAVE" for status in statuses)
            absence = sum(status == "ABSENCE" for status in statuses)
            not_working = sum(status in NOT_WORKING_STATUSES for status in statuses)
            summaries[day] = DailyScheduleSummary(
                working=max(0, total_employees - not_working),
                day_off=day_off,
                vacation=vacation,
                medical_leave=medical_leave,
                absence=absence,
            )
        return summaries

    def set_status(
        self, employee_id: int, year: int, month: int, day: int, status: str | None
    ) -> None:
        if status is not None and status not in VALID_STATUSES:
            raise ValueError("Status de escala inválido.")
        self.repository.set_status(employee_id, date(year, month, day), status)

    def set_day_off_employees(
        self,
        year: int,
        month: int,
        day: int,
        selected_employee_ids: set[int],
    ) -> set[int]:
        if any(employee_id <= 0 for employee_id in selected_employee_ids):
            raise ValueError("Funcionário inválido.")
        return self.repository.set_day_off_employees(
            date(year, month, day), selected_employee_ids
        )

    def copy_previous_month(self, year: int, month: int) -> int:
        return self.repository.replace_with_previous_month(year, month)
