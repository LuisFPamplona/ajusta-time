from __future__ import annotations

import calendar
from datetime import date, datetime

from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from app.database.repositories.employee_repository import Employee
from app.database.repositories.schedule_repository import ScheduleEntry
from app.database.repositories.settings_repository import SettingsRepository
from app.services.employee_service import EmployeeService
from app.services.print_service import PrintService
from app.services.schedule_service import ScheduleService
from app.ui.day_off_dialog import DayOffDialog
from app.ui.icons import line_icon
from app.ui.schedule_calendar import ScheduleCalendarWidget, SummaryCard

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
        self._employees: list[Employee] = []
        self._entries: dict[tuple[int, int], str] = {}
        self._entry_details: dict[tuple[int, int], ScheduleEntry] = {}
        today = datetime.now().astimezone().date()

        title = QLabel("Escala mensal")
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "Visualize quantos funcionários estão de folga em cada dia do mês."
        )
        subtitle.setObjectName("pageSubtitle")
        heading = QVBoxLayout()
        heading.setContentsMargins(0, 0, 0, 0)
        heading.setSpacing(2)
        heading.addWidget(title)
        heading.addWidget(subtitle)

        copy_button = QPushButton("Copiar mês anterior")
        copy_button.setIcon(line_icon("copy"))
        print_button = QPushButton("Imprimir")
        print_button.setObjectName("primaryButton")
        print_button.setIcon(line_icon("print", "#ffffff"))
        copy_button.clicked.connect(self.copy_previous_month)
        print_button.clicked.connect(self.print_schedule)
        actions = QHBoxLayout()
        actions.setSpacing(10)
        actions.addWidget(copy_button)
        actions.addWidget(print_button)

        top_row = QHBoxLayout()
        top_row.addLayout(heading, 1)
        top_row.addLayout(actions)

        previous_button = QPushButton()
        previous_button.setObjectName("navButton")
        previous_button.setToolTip("Mês anterior")
        previous_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowLeft)
        )
        next_button = QPushButton()
        next_button.setObjectName("navButton")
        next_button.setToolTip("Próximo mês")
        next_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowRight)
        )
        previous_button.clicked.connect(self.show_previous_month)
        next_button.clicked.connect(self.show_next_month)

        self.month_combo = QComboBox()
        self.month_combo.addItems(MONTH_NAMES)
        self.month_combo.setCurrentIndex(today.month - 1)
        self.month_combo.setMinimumWidth(160)
        self.year_spin = QSpinBox()
        self.year_spin.setRange(1900, 2200)
        self.year_spin.setValue(today.year)
        self.year_spin.setMinimumWidth(115)
        self.month_combo.currentIndexChanged.connect(self.reload)
        self.year_spin.valueChanged.connect(self.reload)

        period_controls = QHBoxLayout()
        period_controls.setSpacing(10)
        period_controls.addWidget(previous_button)
        period_controls.addWidget(self.month_combo)
        period_controls.addWidget(self.year_spin)
        period_controls.addWidget(next_button)
        period_controls.addStretch()

        self.total_card = SummaryCard("users", "Total de folgas no mês", "blue")
        self.maximum_card = SummaryCard("calendar", "Dia com mais folgas", "red")
        self.employees_card = SummaryCard("users", "Funcionários cadastrados", "green")
        cards = QHBoxLayout()
        cards.setSpacing(14)
        cards.addWidget(self.total_card)
        cards.addWidget(self.maximum_card)
        cards.addWidget(self.employees_card)

        self.calendar = ScheduleCalendarWidget()
        self.calendar.day_clicked.connect(self.open_day)

        count_legend = QLabel(
            '<span style="color:#1769e8">●</span>&nbsp; 1 ou mais de folga'
            '&nbsp;&nbsp;&nbsp;&nbsp; <span style="color:#c92333">●</span>&nbsp; '
            "Maior número de folgas no mês"
        )
        count_legend.setObjectName("legend")
        status_legend = QLabel(
            "F = Folga    •    FE = Férias    •    AT = Atestado    •    FA = Falta"
        )
        status_legend.setObjectName("legend")
        legends = QHBoxLayout()
        legends.addWidget(count_legend)
        legends.addStretch()
        legends.addWidget(status_legend)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 22, 30, 12)
        layout.setSpacing(13)
        layout.addLayout(top_row)
        layout.addLayout(period_controls)
        layout.addLayout(cards)
        layout.addWidget(self.calendar, 1)
        layout.addLayout(legends)
        self.reload()

    @property
    def selected_month(self) -> int:
        return self.month_combo.currentIndex() + 1

    @property
    def selected_year(self) -> int:
        return self.year_spin.value()

    def reload(self) -> None:
        year, month = self.selected_year, self.selected_month
        days_in_month = calendar.monthrange(year, month)[1]
        self._employees = self.employee_service.list_employees()
        entry_list = self.schedule_service.get_month_schedule(
            year, month, self._employees
        )
        self._entries = {
            (entry.employee_id, entry.date.day): entry.status for entry in entry_list
        }
        self._entry_details = {
            (entry.employee_id, entry.date.day): entry for entry in entry_list
        }

        employee_names = {employee.id: employee.name for employee in self._employees}
        day_off_names = {day: [] for day in range(1, days_in_month + 1)}
        for entry in entry_list:
            if entry.status == "DAY_OFF" and entry.employee_id in employee_names:
                day_off_names[entry.date.day].append(employee_names[entry.employee_id])
        for names in day_off_names.values():
            names.sort(key=str.casefold)

        total_day_offs = sum(len(names) for names in day_off_names.values())
        maximum_day = None
        maximum_count = 0
        if total_day_offs:
            maximum_day = max(day_off_names, key=lambda day: len(day_off_names[day]))
            maximum_count = len(day_off_names[maximum_day])

        day_off_word = "folga" if total_day_offs == 1 else "folgas"
        self.total_card.set_content(str(total_day_offs), day_off_word)
        if maximum_day is None:
            self.maximum_card.set_content("Nenhuma folga registrada")
        else:
            employee_word = "funcionário" if maximum_count == 1 else "funcionários"
            self.maximum_card.set_content(
                f"{maximum_day} de {MONTH_NAMES[month - 1].lower()}",
                f"{maximum_count} {employee_word}",
            )
        employee_count = len(self._employees)
        employee_word = "funcionário" if employee_count == 1 else "funcionários"
        self.employees_card.set_content(str(employee_count), employee_word)
        self.calendar.set_month(
            year,
            month,
            day_off_names,
            maximum_day,
            MONTH_NAMES[month - 1],
        )

    def show_previous_month(self) -> None:
        if self.selected_year == self.year_spin.minimum() and self.selected_month == 1:
            return
        year = (
            self.selected_year - 1 if self.selected_month == 1 else self.selected_year
        )
        month = 12 if self.selected_month == 1 else self.selected_month - 1
        self._set_period(year, month)

    def show_next_month(self) -> None:
        if self.selected_year == self.year_spin.maximum() and self.selected_month == 12:
            return
        year = (
            self.selected_year + 1 if self.selected_month == 12 else self.selected_year
        )
        month = 1 if self.selected_month == 12 else self.selected_month + 1
        self._set_period(year, month)

    def _set_period(self, year: int, month: int) -> None:
        month_blocker = QSignalBlocker(self.month_combo)
        year_blocker = QSignalBlocker(self.year_spin)
        self.month_combo.setCurrentIndex(month - 1)
        self.year_spin.setValue(year)
        del month_blocker, year_blocker
        self.reload()

    def open_day(self, selected_date: date) -> None:
        entries = {
            employee.id: entry
            for employee in self._employees
            if (entry := self._entry_details.get((employee.id, selected_date.day)))
        }
        dialog = DayOffDialog(
            selected_date,
            MONTH_NAMES[selected_date.month - 1],
            self._employees,
            entries,
            self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            blocked_ids = self.schedule_service.set_day_off_employees(
                selected_date.year,
                selected_date.month,
                selected_date.day,
                dialog.selected_employee_ids(),
            )
        except Exception as error:  # noqa: BLE001 - limite da interface gráfica
            QMessageBox.critical(
                self, "Folgas", f"Não foi possível salvar as folgas.\n\n{error}"
            )
            return
        self.reload()
        if blocked_ids:
            QMessageBox.warning(
                self,
                "Folgas",
                "Alguns funcionários não foram alterados porque possuem outra "
                "ocorrência nesta data.",
            )

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
        settings = self.settings_repository.get_all()
        try:
            self.print_service.show_preview(
                self,
                self.selected_year,
                self.selected_month,
                self._employees,
                self._entries,
                settings,
            )
        except Exception as error:  # noqa: BLE001 - limite da interface gráfica
            QMessageBox.critical(
                self,
                "Impressão",
                f"Não foi possível gerar a impressão.\n\n{error}",
            )
