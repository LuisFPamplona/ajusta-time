from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import date
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

    def test_default_day_off_accepts_only_null_or_weekday_number(self) -> None:
        with self.assertRaises(ValueError):
            self.employees.add_employee("Inválido", 7)
        with self.assertRaises(ValueError):
            self.employees.add_employee("Inválido", -1)
        employee = self.employees.add_employee("Sem folga", None)
        self.assertIsNone(employee.default_day_off)

    def test_existing_database_is_migrated_without_losing_data(self) -> None:
        legacy_path = Path(self.temp_directory.name) / "legacy.db"
        with closing(sqlite3.connect(legacy_path)) as connection, connection:
            connection.executescript(
                """
                CREATE TABLE employees (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
                CREATE TABLE schedule_entries (
                    id INTEGER PRIMARY KEY,
                    employee_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    status TEXT NOT NULL,
                    notes TEXT,
                    UNIQUE(employee_id, date),
                    FOREIGN KEY(employee_id) REFERENCES employees(id)
                );
                CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT);
                INSERT INTO employees(id, name) VALUES (10, 'Funcionário legado');
                INSERT INTO schedule_entries(
                    id, employee_id, date, status, notes
                ) VALUES (20, 10, '2026-09-10', 'DAY_OFF', NULL);
                """
            )
        legacy_database = Database(legacy_path)
        initialize_database(legacy_database)
        initialize_database(legacy_database)
        with legacy_database.connection() as connection:
            employee = connection.execute(
                "SELECT name, default_day_off FROM employees WHERE id = 10"
            ).fetchone()
            entry = connection.execute(
                "SELECT status, source FROM schedule_entries WHERE id = 20"
            ).fetchone()
        self.assertEqual(employee["name"], "Funcionário legado")
        self.assertIsNone(employee["default_day_off"])
        self.assertEqual(entry["status"], "DAY_OFF")
        self.assertEqual(entry["source"], "MANUAL")

    def test_default_weekly_days_are_generated_for_common_month_lengths(self) -> None:
        employee = self.employees.list_employees()[0]
        self.employees.update_employee(employee.id, employee.name, 0, date(2026, 1, 1))
        employee = self.employees.list_employees()[0]
        no_default = self.employees.list_employees()[1]

        september = self.schedule.get_month_schedule(
            2026, 9, [employee, no_default], date(2026, 9, 1)
        )
        self.assertEqual(
            [entry.date.day for entry in september if entry.employee_id == employee.id],
            [7, 14, 21, 28],
        )
        self.assertFalse(any(entry.employee_id == no_default.id for entry in september))
        self.assertTrue(all(entry.source == "DEFAULT" for entry in september))

        self.employees.update_employee(employee.id, employee.name, 6, date(2027, 1, 1))
        employee = self.employees.list_employees()[0]
        february = self.schedule.get_month_schedule(
            2027, 2, [employee], date(2027, 2, 1)
        )
        self.assertEqual([entry.date.day for entry in february], [7, 14, 21, 28])

        self.employees.update_employee(employee.id, employee.name, 1, date(2028, 1, 1))
        employee = self.employees.list_employees()[0]
        leap_february = self.schedule.get_month_schedule(
            2028, 2, [employee], date(2028, 2, 1)
        )
        self.assertEqual(
            [entry.date.day for entry in leap_february], [1, 8, 15, 22, 29]
        )

        self.employees.update_employee(employee.id, employee.name, 6, date(2027, 8, 1))
        employee = self.employees.list_employees()[0]
        august = self.schedule.get_month_schedule(2027, 8, [employee], date(2027, 8, 1))
        self.assertTrue(all(entry.date.weekday() == 6 for entry in august))
        self.assertTrue(any(entry.date.day == 29 for entry in august))

    def test_changing_default_preserves_history_and_manual_entries(self) -> None:
        employee = self.employees.list_employees()[0]
        self.employees.update_employee(employee.id, employee.name, 0, date(2026, 9, 1))
        employee = self.employees.list_employees()[0]
        self.schedule.get_month_schedule(2026, 9, [employee], date(2026, 9, 1))
        self.schedule.set_status(employee.id, 2026, 9, 18, "DAY_OFF")

        self.employees.update_employee(employee.id, employee.name, 1, date(2026, 9, 9))
        employee = self.employees.list_employees()[0]
        entries = self.schedule.get_month_schedule(
            2026, 9, [employee], date(2026, 9, 9)
        )
        by_day = {entry.date.day: entry for entry in entries}
        self.assertEqual(by_day[7].source, "DEFAULT")
        self.assertEqual(by_day[18].source, "MANUAL")
        self.assertEqual(
            [day for day, entry in by_day.items() if entry.source == "DEFAULT"],
            [7, 15, 22, 29],
        )

    def test_removing_default_keeps_past_default_and_manual_day_off(self) -> None:
        employee = self.employees.list_employees()[0]
        self.employees.update_employee(employee.id, employee.name, 0, date(2026, 9, 1))
        employee = self.employees.list_employees()[0]
        self.schedule.get_month_schedule(2026, 9, [employee], date(2026, 9, 1))
        self.schedule.set_status(employee.id, 2026, 9, 18, "DAY_OFF")

        self.employees.update_employee(
            employee.id, employee.name, None, date(2026, 9, 9)
        )
        entries = self.schedule.month_entry_list(2026, 9)
        by_day = {entry.date.day: entry for entry in entries}
        self.assertEqual(set(by_day), {7, 18})
        self.assertEqual(by_day[7].source, "DEFAULT")
        self.assertEqual(by_day[18].source, "MANUAL")

    def test_work_override_survives_reload_and_can_be_marked_again(self) -> None:
        employee = self.employees.list_employees()[0]
        self.employees.update_employee(employee.id, employee.name, 0, date(2026, 9, 1))
        employee = self.employees.list_employees()[0]
        self.schedule.get_month_schedule(2026, 9, [employee], date(2026, 9, 1))

        self.schedule.set_day_off_employees(2026, 9, 14, set())
        reloaded = self.schedule.get_month_schedule(
            2026, 9, [employee], date(2026, 9, 1)
        )
        override = next(entry for entry in reloaded if entry.date.day == 14)
        self.assertEqual(override.status, "WORK_OVERRIDE")
        self.assertEqual(override.source, "MANUAL")

        self.schedule.set_day_off_employees(2026, 9, 14, {employee.id})
        restored = next(
            entry
            for entry in self.schedule.month_entry_list(2026, 9)
            if entry.date.day == 14
        )
        self.assertEqual(restored.status, "DAY_OFF")
        self.assertEqual(restored.source, "MANUAL")

    def test_other_statuses_take_priority_over_weekly_default(self) -> None:
        employee = self.employees.list_employees()[0]
        self.employees.update_employee(employee.id, employee.name, 0, date(2026, 9, 1))
        employee = self.employees.list_employees()[0]
        statuses = {14: "VACATION", 21: "MEDICAL_LEAVE", 28: "ABSENCE"}
        for day, status in statuses.items():
            self.schedule.set_status(employee.id, 2026, 9, day, status)

        entries = self.schedule.get_month_schedule(
            2026, 9, [employee], date(2026, 9, 1)
        )
        by_day = {entry.date.day: entry.status for entry in entries}
        self.assertEqual(by_day[7], "DAY_OFF")
        for day, status in statuses.items():
            self.assertEqual(by_day[day], status)

    def test_employee_with_schedule_cannot_be_deleted(self) -> None:
        employee = self.employees.list_employees()[0]
        self.schedule.set_status(employee.id, 2026, 9, 3, "VACATION")
        with self.assertRaises(EmployeeHasScheduleError):
            self.employees.delete_employee(employee.id)

    def test_day_off_dialog_update_preserves_other_statuses(self) -> None:
        first, second, third = self.employees.list_employees()
        self.schedule.set_status(first.id, 2026, 9, 15, "VACATION")
        self.schedule.set_status(second.id, 2026, 9, 15, "DAY_OFF")

        blocked = self.schedule.set_day_off_employees(2026, 9, 15, {first.id, third.id})

        entries = self.schedule.month_entries(2026, 9)
        self.assertEqual(blocked, {first.id})
        self.assertEqual(entries[(first.id, 15)], "VACATION")
        self.assertNotIn((second.id, 15), entries)
        self.assertEqual(entries[(third.id, 15)], "DAY_OFF")

    def test_copy_previous_month_replaces_target_and_skips_invalid_days(self) -> None:
        employee = self.employees.list_employees()[0]
        self.schedule.set_status(employee.id, 2026, 1, 31, "DAY_OFF")
        self.schedule.set_status(employee.id, 2026, 1, 28, "VACATION")
        self.schedule.repository.set_status(
            employee.id, date(2026, 1, 5), "DAY_OFF", source="DEFAULT"
        )
        self.schedule.set_status(employee.id, 2026, 1, 12, "WORK_OVERRIDE")
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

    def test_json_backup_preserves_new_fields_and_accepts_legacy_backup(self) -> None:
        backup_service = BackupService(self.database)
        employee = self.employees.list_employees()[0]
        self.employees.update_employee(employee.id, employee.name, 6, date(2026, 9, 1))
        employee = self.employees.list_employees()[0]
        self.schedule.get_month_schedule(2026, 9, [employee], date(2026, 9, 1))
        backup_path = Path(self.temp_directory.name) / "new-backup.json"
        backup_service.export_json(backup_path)
        payload = json.loads(backup_path.read_text(encoding="utf-8"))
        exported_employee = next(
            item for item in payload["employees"] if item["id"] == employee.id
        )
        self.assertEqual(exported_employee["default_day_off"], 6)
        self.assertTrue(all("source" in item for item in payload["schedule_entries"]))

        for item in payload["employees"]:
            item.pop("default_day_off")
        for item in payload["schedule_entries"]:
            item.pop("source")
        legacy_path = Path(self.temp_directory.name) / "legacy-backup.json"
        legacy_path.write_text(json.dumps(payload), encoding="utf-8")
        backup_service.import_json(legacy_path)

        imported_employee = next(
            item for item in self.employees.list_employees() if item.id == employee.id
        )
        self.assertIsNone(imported_employee.default_day_off)
        self.assertTrue(
            all(
                entry.source == "MANUAL"
                for entry in self.schedule.month_entry_list(2026, 9)
            )
        )


if __name__ == "__main__":
    unittest.main()
