from __future__ import annotations

import logging
import os
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from app.database.connection import Database
from app.database.repositories.employee_repository import EmployeeRepository
from app.database.repositories.leave_repository import LeaveRepository
from app.database.repositories.schedule_repository import ScheduleRepository
from app.database.repositories.settings_repository import SettingsRepository
from app.database.schema import initialize_database
from app.logging_config import configure_logging
from app.paths import (
    DATA_DIR_ENV,
    get_app_data_dir,
    get_database_path,
    migrate_legacy_database,
)
from app.services.backup_service import BackupService
from app.services.employee_service import EmployeeService
from app.services.leave_service import LeaveService
from app.services.schedule_service import ScheduleService
from app.version import APP_NAME, APP_VERSION


class ReleaseReadinessTestCase(unittest.TestCase):
    def test_version_has_single_release_source(self) -> None:
        self.assertEqual(APP_NAME, "Ajusta Time")
        self.assertEqual(APP_VERSION, "1.0.0")

    def test_windows_data_path_uses_local_app_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            local_app_data = Path(temporary_directory) / "Local"
            environment = {"LOCALAPPDATA": str(local_app_data)}
            with (
                patch.dict(os.environ, environment, clear=True),
                patch("app.paths.sys.platform", "win32"),
            ):
                self.assertEqual(
                    get_app_data_dir(), (local_app_data / "AjustaTime").resolve()
                )
                self.assertEqual(
                    get_database_path(),
                    (local_app_data / "AjustaTime" / "escala.db").resolve(),
                )

    def test_data_directory_override_supports_isolated_first_and_second_runs(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory) / "user-data"
            with patch.dict(os.environ, {DATA_DIR_ENV: str(data_dir)}):
                database_path = get_database_path()
                self.assertFalse(database_path.exists())
                database = Database(database_path)
                initialize_database(database)
                employees = EmployeeService(EmployeeRepository(database))
                created = employees.add_employee("Persistente", 0)

                reopened = Database(get_database_path())
                initialize_database(reopened)
                persisted = EmployeeService(
                    EmployeeRepository(reopened)
                ).list_employees()

            self.assertTrue(database_path.exists())
            self.assertTrue(
                any(
                    employee.id == created.id
                    and employee.name == "Persistente"
                    and employee.default_day_off == 0
                    for employee in persisted
                )
            )

    def test_legacy_database_migration_validates_and_never_overwrites(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            legacy = root / "legacy" / "escala.db"
            destination = root / "new" / "escala.db"
            legacy_database = Database(legacy)
            initialize_database(legacy_database)
            service = EmployeeService(EmployeeRepository(legacy_database))
            employee = service.add_employee("Banco legado", 2)

            self.assertTrue(migrate_legacy_database(destination, legacy))
            migrated = EmployeeService(EmployeeRepository(Database(destination)))
            self.assertTrue(
                any(
                    item.id == employee.id and item.name == employee.name
                    for item in migrated.list_employees()
                )
            )

            with sqlite3.connect(destination) as connection:
                connection.execute(
                    "INSERT INTO employees(name) VALUES (?)", ("Somente destino",)
                )
            self.assertFalse(migrate_legacy_database(destination, legacy))
            names = {
                item.name
                for item in EmployeeService(
                    EmployeeRepository(Database(destination))
                ).list_employees()
            }
            self.assertIn("Somente destino", names)

    def test_invalid_legacy_file_is_not_migrated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            legacy = root / "invalid.db"
            destination = root / "data" / "escala.db"
            legacy.write_text("não é sqlite", encoding="utf-8")
            self.assertFalse(migrate_legacy_database(destination, legacy))
            self.assertFalse(destination.exists())

    def test_schema_is_idempotent_and_foreign_keys_are_valid(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database = Database(Path(temporary_directory) / "escala.db")
            initialize_database(database)
            initialize_database(database)
            with database.connection() as connection:
                self.assertEqual(
                    connection.execute("PRAGMA user_version").fetchone()[0], 2
                )
                self.assertEqual(
                    connection.execute("PRAGMA foreign_keys").fetchone()[0], 1
                )
                self.assertEqual(
                    connection.execute("PRAGMA foreign_key_check").fetchall(), []
                )
                indexes = {
                    row["name"]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = ?", ("index",)
                    )
                }
            self.assertIn("idx_leave_periods_employee_dates", indexes)
            self.assertIn("idx_schedule_entries_leave_period", indexes)

    def test_logging_writes_utf8_to_rotating_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            log_directory = Path(temporary_directory) / "logs"
            logger = configure_logging(log_directory)
            try:
                logger.info("Inicialização de teste: férias e funcionários.")
                for handler in logger.handlers:
                    handler.flush()
                content = (log_directory / "ajusta-time.log").read_text(
                    encoding="utf-8"
                )
                self.assertIn("férias e funcionários", content)
                rotating_handlers = [
                    handler
                    for handler in logger.handlers
                    if isinstance(handler, logging.handlers.RotatingFileHandler)
                ]
                self.assertEqual(len(rotating_handlers), 1)
                self.assertEqual(rotating_handlers[0].maxBytes, 1_000_000)
                self.assertEqual(rotating_handlers[0].backupCount, 3)
            finally:
                for handler in list(logger.handlers):
                    if isinstance(handler, logging.handlers.RotatingFileHandler):
                        logger.removeHandler(handler)
                        handler.close()

    def test_complete_business_flow_persists_after_reopening(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            database_path = root / "escala.db"
            database = Database(database_path)
            initialize_database(database)
            employees = EmployeeService(EmployeeRepository(database))
            schedule = ScheduleService(ScheduleRepository(database))
            leaves = LeaveService(LeaveRepository(database))
            for employee in employees.list_employees():
                employees.delete_employee(employee.id)
            joao = employees.add_employee("João Silva", 0)
            maria = employees.add_employee("Maria Souza", 2)

            schedule.get_month_schedule(2026, 9, [joao, maria], date(2026, 9, 1))
            schedule.set_status(joao.id, 2026, 9, 3, "DAY_OFF")
            schedule.set_day_off_employees(2026, 9, 14, set())
            vacation = leaves.create_leave(
                joao.id,
                "VACATION",
                date(2026, 9, 21),
                date(2026, 9, 25),
            )
            medical_leave = leaves.create_leave(
                maria.id,
                "MEDICAL_LEAVE",
                date(2026, 9, 16),
                date(2026, 9, 17),
            )
            SettingsRepository(database).save({"company_name": "Empresa Teste"})

            entries = schedule.month_entry_list(2026, 9)
            self.assertEqual(
                next(
                    entry.status
                    for entry in entries
                    if entry.employee_id == joao.id and entry.date.day == 14
                ),
                "WORK_OVERRIDE",
            )
            self.assertEqual(sum(entry.status == "DAY_OFF" for entry in entries), 7)
            self.assertEqual(vacation.days, 5)
            self.assertEqual(medical_leave.days, 2)

            backup = BackupService(database)
            json_path = root / "backup.json"
            sqlite_path = root / "backup.db"
            backup.export_json(json_path)
            backup.create_database_backup(sqlite_path)

            reopened = Database(database_path)
            initialize_database(reopened)
            reopened_entries = ScheduleRepository(reopened).list_month(2026, 9)
            reopened_leaves = LeaveRepository(reopened).list_all()
            reopened_settings = SettingsRepository(reopened).get_all()
            self.assertEqual(len(reopened_entries), len(entries))
            self.assertEqual(len(reopened_leaves), 2)
            self.assertEqual(reopened_settings["company_name"], "Empresa Teste")
            self.assertTrue(json_path.is_file())
            with sqlite3.connect(sqlite_path) as connection:
                self.assertEqual(
                    connection.execute("PRAGMA integrity_check").fetchone()[0], "ok"
                )


if __name__ == "__main__":
    unittest.main()
