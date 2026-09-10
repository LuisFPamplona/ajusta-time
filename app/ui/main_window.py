from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QMainWindow, QTabWidget

from app.database.connection import Database
from app.database.repositories.employee_repository import EmployeeRepository
from app.database.repositories.schedule_repository import ScheduleRepository
from app.database.repositories.settings_repository import SettingsRepository
from app.services.backup_service import BackupService
from app.services.employee_service import EmployeeService
from app.services.print_service import PrintService
from app.services.schedule_service import ScheduleService
from app.ui.employees_page import EmployeesPage
from app.ui.icons import line_icon
from app.ui.schedule_page import SchedulePage
from app.ui.settings_page import SettingsPage
from app.ui.theme import APP_STYLE_SHEET


class MainWindow(QMainWindow):
    def __init__(self, database: Database) -> None:
        super().__init__()
        self.setWindowTitle("Ajusta Time")
        self.resize(1366, 820)
        self.setMinimumSize(1050, 700)
        self.setStyleSheet(APP_STYLE_SHEET)

        employee_service = EmployeeService(EmployeeRepository(database))
        schedule_service = ScheduleService(ScheduleRepository(database))
        settings_repository = SettingsRepository(database)

        self.schedule_page = SchedulePage(
            employee_service,
            schedule_service,
            settings_repository,
            PrintService(),
        )
        self.employees_page = EmployeesPage(employee_service)
        self.settings_page = SettingsPage(settings_repository, BackupService(database))

        self.employees_page.employees_changed.connect(self.schedule_page.reload)
        self.settings_page.data_imported.connect(self._reload_all)

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.setIconSize(QSize(20, 20))
        tabs.addTab(
            self.schedule_page,
            line_icon("calendar", "#1769e8"),
            "Escala",
        )
        tabs.addTab(
            self.employees_page,
            line_icon("users"),
            "Funcionários",
        )
        tabs.addTab(
            self.settings_page,
            line_icon("settings"),
            "Configurações",
        )
        tabs.setCurrentIndex(0)
        self.setCentralWidget(tabs)

    def _reload_all(self) -> None:
        self.employees_page.reload()
        self.schedule_page.reload()
        self.settings_page.reload()
