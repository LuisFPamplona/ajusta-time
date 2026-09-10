from __future__ import annotations

import calendar
from datetime import datetime

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.database.repositories.settings_repository import SettingsRepository
from app.services.employee_service import EmployeeService
from app.services.print_service import WEEKDAY_NAMES, PrintService
from app.services.schedule_service import STATUS_LABELS, STATUS_NAMES, ScheduleService

MONTH_NAMES = (
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
)

STATUS_COLORS = {
    "DAY_OFF": QColor("#d8ecff"),
    "VACATION": QColor("#dcf4e4"),
    "MEDICAL_LEAVE": QColor("#fff0c7"),
    "ABSENCE": QColor("#ffd9d9"),
}


class SchedulePage(QWidget):
    def __init__(
        self,
        employee_service: EmployeeService,
        schedule_service: ScheduleService,
        settings_repository: SettingsRepository,
        print_service: PrintService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.employee_service = employee_service
        self.schedule_service = schedule_service
        self.settings_repository = settings_repository
        self.print_service = print_service
        today = datetime.now().astimezone().date()

        title = QLabel("Escala mensal")
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "Clique com o botão direito em um dia para registrar uma ocorrência."
        )
        subtitle.setObjectName("pageSubtitle")

        self.month_combo = QComboBox()
        self.month_combo.addItems(MONTH_NAMES)
        self.month_combo.setCurrentIndex(today.month - 1)
        self.year_spin = QSpinBox()
        self.year_spin.setRange(1900, 2200)
        self.year_spin.setValue(today.year)
        self.year_spin.setButtonSymbols(QSpinBox.ButtonSymbols.PlusMinus)
        self.month_combo.currentIndexChanged.connect(self.reload)
        self.year_spin.valueChanged.connect(self.reload)

        copy_button = QPushButton("Copiar mês anterior")
        print_button = QPushButton("Imprimir")
        copy_button.clicked.connect(self.copy_previous_month)
        print_button.clicked.connect(self.print_schedule)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Mês:"))
        controls.addWidget(self.month_combo)
        controls.addWidget(QLabel("Ano:"))
        controls.addWidget(self.year_spin)
        controls.addStretch()
        controls.addWidget(copy_button)
        controls.addWidget(print_button)

        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.open_context_menu)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setMinimumHeight(48)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.table.setWordWrap(True)

        legend = QLabel(
            "F = Folga    •    FE = Férias    •    AT = Atestado    •    FA = Falta"
        )
        legend.setObjectName("legend")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(8)
        layout.addLayout(controls)
        layout.addWidget(self.table, 1)
        layout.addWidget(legend)
        self.reload()

    @property
    def selected_month(self) -> int:
        return self.month_combo.currentIndex() + 1

    @property
    def selected_year(self) -> int:
        return self.year_spin.value()

    def reload(self) -> None:
        year, month = self.selected_year, self.selected_month
        days = calendar.monthrange(year, month)[1]
        employees = self.employee_service.list_employees()
        entries = self.schedule_service.month_entries(year, month)

        self.table.clear()
        self.table.setRowCount(len(employees))
        self.table.setColumnCount(days + 1)
        headers = ["Funcionário"] + [
            f"{day:02d}\n{WEEKDAY_NAMES[calendar.weekday(year, month, day)]}"
            for day in range(1, days + 1)
        ]
        self.table.setHorizontalHeaderLabels(headers)
        for day in range(1, days + 1):
            if calendar.weekday(year, month, day) >= 5:
                self.table.horizontalHeaderItem(day).setBackground(QColor("#d4d8dd"))
        self.table.setColumnWidth(0, 210)
        self.table.horizontalHeader().setMinimumSectionSize(43)
        for column in range(1, days + 1):
            self.table.setColumnWidth(column, 48)
        for row, employee in enumerate(employees):
            self.table.setRowHeight(row, 36)
            name_item = QTableWidgetItem(employee.name)
            name_item.setToolTip(employee.name)
            name_item.setData(Qt.ItemDataRole.UserRole, employee.id)
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 0, name_item)
            for day in range(1, days + 1):
                status = entries.get((employee.id, day))
                item = QTableWidgetItem(STATUS_LABELS.get(status, ""))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setData(Qt.ItemDataRole.UserRole, status)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                if status:
                    item.setBackground(STATUS_COLORS[status])
                    item.setToolTip(STATUS_NAMES[status])
                elif calendar.weekday(year, month, day) >= 5:
                    item.setBackground(QColor("#f0f0f0"))
                self.table.setItem(row, day, item)

    def open_context_menu(self, position: QPoint) -> None:
        item = self.table.itemAt(position)
        if item is None or item.column() == 0:
            return
        row, day = item.row(), item.column()
        employee_id = int(self.table.item(row, 0).data(Qt.ItemDataRole.UserRole))
        menu = QMenu(self)
        choices: tuple[tuple[str, str | None], ...] = (
            ("Folga (F)", "DAY_OFF"),
            ("Férias (FE)", "VACATION"),
            ("Atestado (AT)", "MEDICAL_LEAVE"),
            ("Falta (FA)", "ABSENCE"),
            ("", None),
            ("Limpar", None),
        )
        actions: dict[QAction, str | None] = {}
        for label, status in choices:
            if not label:
                menu.addSeparator()
                continue
            action = menu.addAction(label)
            actions[action] = status
        chosen = menu.exec(self.table.viewport().mapToGlobal(position))
        if chosen is None:
            return
        try:
            self.schedule_service.set_status(
                employee_id,
                self.selected_year,
                self.selected_month,
                day,
                actions[chosen],
            )
        except Exception as error:  # noqa: BLE001 - limite da interface gráfica
            QMessageBox.critical(
                self, "Escala", f"Não foi possível salvar a alteração.\n\n{error}"
            )
            return
        self.reload()

    def copy_previous_month(self) -> None:
        month_name = MONTH_NAMES[self.selected_month - 1]
        answer = QMessageBox.question(
            self,
            "Copiar mês anterior",
            f"Substituir as ocorrências de {month_name}/{self.selected_year} "
            "pelas do mês anterior?\n\nDatas que não existem no mês de destino "
            "serão ignoradas.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            copied = self.schedule_service.copy_previous_month(
                self.selected_year, self.selected_month
            )
        except Exception as error:  # noqa: BLE001 - limite da interface gráfica
            QMessageBox.critical(
                self, "Escala", f"Não foi possível copiar a escala.\n\n{error}"
            )
            return
        self.reload()
        QMessageBox.information(
            self, "Escala", f"Cópia concluída: {copied} ocorrência(s)."
        )

    def print_schedule(self) -> None:
        employees = self.employee_service.list_employees()
        entries = self.schedule_service.month_entries(
            self.selected_year, self.selected_month
        )
        settings = self.settings_repository.get_all()
        try:
            self.print_service.show_preview(
                self,
                self.selected_year,
                self.selected_month,
                employees,
                entries,
                settings,
            )
        except Exception as error:  # noqa: BLE001 - limite da interface gráfica
            QMessageBox.critical(
                self,
                "Impressão",
                f"Não foi possível gerar a impressão.\n\n{error}",
            )
