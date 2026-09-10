from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import date
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QTabWidget

from app.database.connection import Database
from app.database.repositories.employee_repository import (
    EmployeeHasScheduleError,
    EmployeeRepository,
)
from app.database.repositories.leave_repository import LeaveRepository
from app.database.repositories.schedule_repository import ScheduleRepository
from app.database.repositories.settings_repository import SettingsRepository
from app.database.schema import initialize_database
from app.services.backup_service import BackupService
from app.services.employee_service import EmployeeService
from app.services.leave_service import (
    LeaveConflictError,
    LeaveOverlapError,
    LeaveService,
)
from app.services.print_service import PrintService
from app.services.schedule_service import STATUS_LABELS, ScheduleService
from app.ui.day_off_dialog import DayOffDialog
from app.ui.main_window import MainWindow
from app.ui.schedule_page import SchedulePage
from app.ui.theme import apply_app_theme


class LeaveTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])
        apply_app_theme(cls.application)

    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_directory.name) / "escala.db")
        initialize_database(self.database)
        self.employees = EmployeeService(EmployeeRepository(self.database))
        self.schedule = ScheduleService(ScheduleRepository(self.database))
        self.leaves = LeaveService(LeaveRepository(self.database))
        self.employee = self.employees.list_employees()[0]

    def tearDown(self) -> None:
        self.temp_directory.cleanup()

    def test_single_and_multiple_day_leave_projections(self) -> None:
        cases = (
            ("VACATION", date(2026, 10, 1), date(2026, 10, 1), 1),
            ("MEDICAL_LEAVE", date(2026, 10, 8), date(2026, 10, 8), 1),
            ("MEDICAL_LEAVE", date(2026, 11, 3), date(2026, 11, 7), 5),
            ("VACATION", date(2027, 1, 1), date(2027, 1, 30), 30),
        )
        for leave_type, start, end, expected_days in cases:
            with self.subTest(leave_type=leave_type, start=start, end=end):
                leave = self.leaves.create_leave(
                    self.employee.id, leave_type, start, end
                )
                self.assertEqual(leave.days, expected_days)
                with self.database.connection() as connection:
                    rows = connection.execute(
                        """
                        SELECT status, source, leave_period_id
                        FROM schedule_entries WHERE leave_period_id = ?
                        ORDER BY date
                        """,
                        (leave.id,),
                    ).fetchall()
                self.assertEqual(len(rows), expected_days)
                self.assertTrue(
                    all(
                        row["status"] == leave_type
                        and row["source"] == "LEAVE"
                        and row["leave_period_id"] == leave.id
                        for row in rows
                    )
                )
                self.leaves.delete_leave(leave.id)

    def test_leave_can_cross_month_and_year_boundaries(self) -> None:
        periods = (
            ("VACATION", date(2026, 9, 28), date(2026, 10, 3)),
            ("MEDICAL_LEAVE", date(2026, 10, 29), date(2026, 11, 4)),
            ("VACATION", date(2026, 12, 29), date(2027, 1, 4)),
        )
        for leave_type, start, end in periods:
            with self.subTest(leave_type=leave_type, start=start, end=end):
                leave = self.leaves.create_leave(
                    self.employee.id, leave_type, start, end
                )
                entries = [
                    *self.schedule.month_entry_list(start.year, start.month),
                    *self.schedule.month_entry_list(end.year, end.month),
                ]
                linked = [
                    entry for entry in entries if entry.leave_period_id == leave.id
                ]
                self.assertEqual(len(linked), leave.days)
                self.leaves.delete_leave(leave.id)

    def test_leave_has_priority_and_deletion_restores_weekly_day_off(self) -> None:
        self.employees.update_employee(
            self.employee.id, self.employee.name, 0, date(2026, 9, 1)
        )
        self.employee = self.employees.list_employees()[0]
        self.schedule.get_month_schedule(2026, 9, [self.employee], date(2026, 9, 1))

        for leave_type in ("VACATION", "MEDICAL_LEAVE"):
            with self.subTest(leave_type=leave_type):
                leave = self.leaves.create_leave(
                    self.employee.id,
                    leave_type,
                    date(2026, 9, 14),
                    date(2026, 9, 20),
                )
                entries = self.schedule.month_entry_list(2026, 9)
                by_day = {
                    entry.date.day: entry
                    for entry in entries
                    if entry.employee_id == self.employee.id
                }
                self.assertEqual(by_day[14].status, leave_type)
                self.assertEqual(by_day[14].source, "LEAVE")
                self.assertEqual(by_day[21].status, "DAY_OFF")

                self.leaves.delete_leave(leave.id)
                restored = self.schedule.month_entry_list(2026, 9)
                by_day = {
                    entry.date.day: entry
                    for entry in restored
                    if entry.employee_id == self.employee.id
                }
                self.assertEqual(by_day[14].status, "DAY_OFF")
                self.assertEqual(by_day[14].source, "DEFAULT")

    def test_edit_rebuilds_projection_and_restores_old_default(self) -> None:
        self.employees.update_employee(
            self.employee.id, self.employee.name, 0, date(2026, 9, 1)
        )
        leave = self.leaves.create_leave(
            self.employee.id,
            "VACATION",
            date(2026, 9, 14),
            date(2026, 9, 20),
        )
        updated = self.leaves.update_leave(
            leave.id,
            self.employee.id,
            "MEDICAL_LEAVE",
            date(2026, 9, 15),
            date(2026, 9, 18),
            "Atestado atualizado",
        )

        self.assertEqual(updated.type, "MEDICAL_LEAVE")
        self.assertEqual(updated.days, 4)
        entries = self.schedule.month_entry_list(2026, 9)
        by_day = {
            entry.date.day: entry
            for entry in entries
            if entry.employee_id == self.employee.id
        }
        self.assertEqual(by_day[14].status, "DAY_OFF")
        self.assertEqual(by_day[14].source, "DEFAULT")
        self.assertEqual(
            [day for day in range(15, 19) if by_day[day].status == "MEDICAL_LEAVE"],
            [15, 16, 17, 18],
        )
        self.assertNotIn(19, by_day)
        self.assertNotIn(20, by_day)

    def test_overlap_is_rejected_without_changing_existing_leave(self) -> None:
        original = self.leaves.create_leave(
            self.employee.id,
            "VACATION",
            date(2026, 9, 10),
            date(2026, 9, 20),
        )
        with self.assertRaises(LeaveOverlapError):
            self.leaves.create_leave(
                self.employee.id,
                "MEDICAL_LEAVE",
                date(2026, 9, 15),
                date(2026, 9, 17),
            )
        self.assertEqual(self.leaves.list_leaves(), [original])
        self.assertEqual(
            len(
                [
                    entry
                    for entry in self.schedule.month_entry_list(2026, 9)
                    if entry.leave_period_id == original.id
                ]
            ),
            original.days,
        )

    def test_invalid_period_is_rejected_before_writing(self) -> None:
        with self.assertRaisesRegex(ValueError, "data inicial"):
            self.leaves.create_leave(
                self.employee.id,
                "VACATION",
                date(2026, 9, 20),
                date(2026, 9, 10),
            )
        self.assertEqual(self.leaves.list_leaves(), [])

    def test_manual_conflict_requires_explicit_replacement(self) -> None:
        self.schedule.set_status(self.employee.id, 2026, 9, 15, "DAY_OFF")
        self.schedule.set_status(self.employee.id, 2026, 9, 18, "ABSENCE")
        with self.assertRaises(LeaveConflictError) as raised:
            self.leaves.create_leave(
                self.employee.id,
                "VACATION",
                date(2026, 9, 14),
                date(2026, 9, 20),
            )
        self.assertEqual(
            [entry.date.day for entry in raised.exception.conflicts], [15, 18]
        )
        self.assertEqual(self.leaves.list_leaves(), [])

        leave = self.leaves.create_leave(
            self.employee.id,
            "VACATION",
            date(2026, 9, 14),
            date(2026, 9, 20),
            replace_conflicts=True,
        )
        self.assertEqual(leave.days, 7)
        self.assertTrue(
            all(
                entry.source == "LEAVE"
                for entry in self.schedule.month_entry_list(2026, 9)
            )
        )

    def test_linked_days_cannot_be_changed_through_manual_schedule_api(self) -> None:
        self.leaves.create_leave(
            self.employee.id,
            "VACATION",
            date(2026, 9, 15),
            date(2026, 9, 15),
        )
        with self.assertRaisesRegex(ValueError, "Afastamentos"):
            self.schedule.set_status(self.employee.id, 2026, 9, 15, "DAY_OFF")
        self.assertEqual(
            self.schedule.month_entries(2026, 9)[(self.employee.id, 15)],
            "VACATION",
        )

    def test_employee_with_leave_cannot_be_deleted(self) -> None:
        self.leaves.create_leave(
            self.employee.id,
            "MEDICAL_LEAVE",
            date(2026, 9, 15),
            date(2026, 9, 15),
        )
        with self.assertRaises(EmployeeHasScheduleError):
            self.employees.delete_employee(self.employee.id)

    def test_copy_previous_month_preserves_target_leave(self) -> None:
        self.schedule.set_status(self.employee.id, 2026, 1, 15, "DAY_OFF")
        leave = self.leaves.create_leave(
            self.employee.id,
            "VACATION",
            date(2026, 2, 15),
            date(2026, 2, 15),
        )
        copied = self.schedule.copy_previous_month(2026, 2)

        entry = self.schedule.month_entry_list(2026, 2)[0]
        self.assertEqual(copied, 0)
        self.assertEqual(entry.status, "VACATION")
        self.assertEqual(entry.leave_period_id, leave.id)

    def test_calendar_count_excludes_leave_and_print_labels_remain_correct(
        self,
    ) -> None:
        second = self.employees.list_employees()[1]
        self.schedule.set_status(second.id, 2026, 9, 15, "DAY_OFF")
        self.leaves.create_leave(
            self.employee.id,
            "VACATION",
            date(2026, 9, 15),
            date(2026, 9, 15),
        )
        page = SchedulePage(
            self.employees,
            self.schedule,
            SettingsRepository(self.database),
            PrintService(),
        )
        page._set_period(2026, 9)
        self.assertEqual(page.total_card.value_label.text(), "1")
        day_widget = page.calendar.day_widgets[date(2026, 9, 15)]
        count_label = day_widget.findChild(QLabel, "countPill")
        self.assertIsNotNone(count_label)
        self.assertIn("1 funcionário", count_label.text())
        self.assertEqual(
            day_widget.toolTip(),
            "15 de setembro de 2026\n\nFolga: 1\nFérias: 1\nAtestado: 0",
        )

        no_absence_widget = page.calendar.day_widgets[date(2026, 9, 16)]
        no_absence_label = no_absence_widget.findChild(QLabel, "countPill")
        self.assertIsNotNone(no_absence_label)
        self.assertEqual(no_absence_label.text(), "3 funcionários")
        self.assertEqual(
            no_absence_widget.toolTip(),
            "16 de setembro de 2026\n\nFolga: 0\nFérias: 0\nAtestado: 0",
        )
        self.assertEqual(STATUS_LABELS["VACATION"], "FE")
        self.assertEqual(STATUS_LABELS["MEDICAL_LEAVE"], "AT")
        self.assertEqual(STATUS_LABELS["WORK_OVERRIDE"], "")
        page.close()

    def test_day_dialog_disables_leave_entries_and_main_window_has_new_tab(
        self,
    ) -> None:
        leave = self.leaves.create_leave(
            self.employee.id,
            "VACATION",
            date(2026, 9, 15),
            date(2026, 9, 15),
        )
        entry = next(
            entry
            for entry in self.schedule.month_entry_list(2026, 9)
            if entry.leave_period_id == leave.id
        )
        dialog = DayOffDialog(
            date(2026, 9, 15),
            "Setembro",
            [self.employee],
            {self.employee.id: entry},
        )
        item = dialog.employee_list.item(0)
        self.assertIn("Férias", item.text())
        self.assertFalse(bool(item.flags() & Qt.ItemFlag.ItemIsEnabled))
        self.assertIn("Afastamentos", item.toolTip())
        dialog.close()

        window = MainWindow(self.database)
        tabs = window.centralWidget()
        self.assertIsInstance(tabs, QTabWidget)
        self.assertEqual(
            [tabs.tabText(index) for index in range(tabs.count())],
            ["Escala", "Funcionários", "Afastamentos", "Configurações"],
        )
        window.close()

    def test_json_backup_round_trip_and_version_one_compatibility(self) -> None:
        backup = BackupService(self.database)
        leave = self.leaves.create_leave(
            self.employee.id,
            "MEDICAL_LEAVE",
            date(2026, 12, 30),
            date(2027, 1, 2),
            "Atestado",
        )
        new_path = Path(self.temp_directory.name) / "new.json"
        backup.export_json(new_path)
        payload = json.loads(new_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["version"], 2)
        self.assertEqual(payload["leave_periods"][0]["id"], leave.id)
        self.assertTrue(
            all(
                item["leave_period_id"] == leave.id
                for item in payload["schedule_entries"]
            )
        )

        self.leaves.delete_leave(leave.id)
        backup.import_json(new_path)
        restored = self.leaves.list_leaves()
        self.assertEqual(len(restored), 1)
        self.assertEqual(restored[0].days, 4)

        payload["version"] = 1
        payload.pop("leave_periods")
        payload["schedule_entries"] = []
        legacy_path = Path(self.temp_directory.name) / "legacy.json"
        legacy_path.write_text(json.dumps(payload), encoding="utf-8")
        backup.import_json(legacy_path)
        self.assertEqual(self.leaves.list_leaves(), [])

    def test_existing_database_migration_preserves_legacy_occurrences(self) -> None:
        legacy_path = Path(self.temp_directory.name) / "legacy-leave.db"
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
                INSERT INTO employees(id, name) VALUES (10, 'Legado');
                INSERT INTO schedule_entries(
                    id, employee_id, date, status, notes
                ) VALUES (20, 10, '2026-09-10', 'VACATION', 'Antiga');
                """
            )
        legacy_database = Database(legacy_path)
        initialize_database(legacy_database)
        with legacy_database.connection() as connection:
            row = connection.execute(
                """
                SELECT id, status, source, leave_period_id
                FROM schedule_entries WHERE id = 20
                """
            ).fetchone()
            leave_table = connection.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'table' AND name = 'leave_periods'
                """
            ).fetchone()
        self.assertEqual(
            dict(row),
            {
                "id": 20,
                "status": "VACATION",
                "source": "MANUAL",
                "leave_period_id": None,
            },
        )
        self.assertIsNotNone(leave_table)


if __name__ == "__main__":
    unittest.main()
