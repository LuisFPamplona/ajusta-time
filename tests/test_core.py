from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.database.connection import Database
from app.database.repositories.employee_repository import (
    EmployeeHasScheduleError,
    EmployeeRepository,
)
from app.database.repositories.schedule_repository import ScheduleRepository
from app.database.schema import initialize_database
from app.services.backup_service import BackupService, BackupValidationError
from app.services.employee_service import EmployeeService
from app.services.schedule_service import ScheduleService


class CoreTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_directory.name) / "escala.db")
        initialize_database(self.database)
        self.employees = EmployeeService(EmployeeRepository(self.database))
        self.schedule = ScheduleService(ScheduleRepository(self.database))

    def tearDown(self) -> None:
        self.temp_directory.cleanup()

    def test_demo_employees_are_not_recreated_after_first_initialization(self) -> None:
        for employee in self.employees.list_employees():
            self.employees.delete_employee(employee.id)
        initialize_database(self.database)
        self.assertEqual(self.employees.list_employees(), [])

    def test_schedule_stores_only_exceptions_and_clear_removes_entry(self) -> None:
        employee = self.employees.list_employees()[0]
        self.schedule.set_status(employee.id, 2026, 9, 3, "DAY_OFF")
        self.assertEqual(
            self.schedule.month_entries(2026, 9)[(employee.id, 3)], "DAY_OFF"
        )
        self.schedule.set_status(employee.id, 2026, 9, 3, None)
        self.assertEqual(self.schedule.month_entries(2026, 9), {})

    def test_default_print_settings_are_persisted(self) -> None:
        with self.database.connection() as connection:
            title = connection.execute(
                "SELECT value FROM settings WHERE key = ?", ("print_title",)
            ).fetchone()[0]
        self.assertEqual(title, "Escala de Folgas")

    def test_employee_with_schedule_cannot_be_deleted(self) -> None:
        employee = self.employees.list_employees()[0]
        self.schedule.set_status(employee.id, 2026, 9, 3, "VACATION")
        with self.assertRaises(EmployeeHasScheduleError):
            self.employees.delete_employee(employee.id)

    def test_copy_previous_month_replaces_target_and_skips_invalid_days(self) -> None:
        employee = self.employees.list_employees()[0]
        self.schedule.set_status(employee.id, 2026, 1, 31, "DAY_OFF")
        self.schedule.set_status(employee.id, 2026, 1, 28, "VACATION")
        self.schedule.set_status(employee.id, 2026, 2, 1, "ABSENCE")
        copied = self.schedule.copy_previous_month(2026, 2)
        entries = self.schedule.month_entries(2026, 2)
        self.assertEqual(copied, 1)
        self.assertEqual(entries, {(employee.id, 28): "VACATION"})

    def test_json_round_trip_and_failed_import_preserves_data(self) -> None:
        backup_service = BackupService(self.database)
        employee = self.employees.list_employees()[0]
        self.schedule.set_status(employee.id, 2026, 9, 9, "MEDICAL_LEAVE")
        backup_path = Path(self.temp_directory.name) / "backup.json"
        backup_service.export_json(backup_path)

        self.schedule.set_status(employee.id, 2026, 9, 9, None)
        backup_service.import_json(backup_path)
        self.assertEqual(
            self.schedule.month_entries(2026, 9)[(employee.id, 9)],
            "MEDICAL_LEAVE",
        )

        invalid_path = Path(self.temp_directory.name) / "invalid.json"
        payload = json.loads(backup_path.read_text(encoding="utf-8"))
        payload["schedule_entries"][0]["employee_id"] = 999999
        invalid_path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaises(BackupValidationError):
            backup_service.import_json(invalid_path)
        self.assertEqual(
            self.schedule.month_entries(2026, 9)[(employee.id, 9)],
            "MEDICAL_LEAVE",
        )


if __name__ == "__main__":
    unittest.main()
