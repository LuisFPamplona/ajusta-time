from __future__ import annotations

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
from app.ui.schedule_page import SchedulePage
from app.ui.settings_page import SettingsPage

STYLE_SHEET = """
QMainWindow { background: #f6f7f9; }
QWidget { font-family: "Segoe UI", Arial, sans-serif; font-size: 10pt; }
QLabel#pageTitle { font-size: 20pt; font-weight: 600; color: #17212b; }
QLabel#pageSubtitle { color: #59636e; }
QLabel#legend { color: #4d5661; padding: 4px; }
QTabWidget::pane { border: 0; background: #ffffff; }
QTabBar::tab { min-width: 130px; padding: 11px 20px; }
QTabBar::tab:selected { background: #ffffff; color: #1557a0; font-weight: 600; }
QPushButton { padding: 7px 14px; }
QTableWidget { background: #ffffff; gridline-color: #d7dce2; }
QHeaderView::section { background: #e9edf2; padding: 5px; border: 1px solid #d1d6dc; font-weight: 600; }
QGroupBox { margin-top: 12px; padding: 12px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
QLineEdit, QComboBox, QSpinBox { padding: 5px; min-height: 20px; }
"""


class MainWindow(QMainWindow):
    def __init__(self, database: Database) -> None:
        super().__init__()
        self.setWindowTitle("Ajusta Time")
        self.resize(1280, 760)
        self.setMinimumSize(900, 600)
        self.setStyleSheet(STYLE_SHEET)

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
        tabs.addTab(self.schedule_page, "Escala")
        tabs.addTab(self.employees_page, "Funcionários")
        tabs.addTab(self.settings_page, "Configurações")
        tabs.setCurrentIndex(0)
        self.setCentralWidget(tabs)

    def _reload_all(self) -> None:
        self.employees_page.reload()
        self.schedule_page.reload()
        self.settings_page.reload()
