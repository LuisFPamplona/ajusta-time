from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.database.repositories.employee_repository import Employee
from app.database.repositories.leave_repository import LeavePeriod
from app.services.leave_service import LEAVE_TYPE_NAMES


class LeaveDialog(QDialog):
    def __init__(
        self,
        employees: list[Employee],
        leave: LeavePeriod | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        title = "Editar afastamento" if leave else "Novo afastamento"
        self.setWindowTitle(title)
        self.setMinimumWidth(500)

        heading = QLabel(title)
        heading.setObjectName("dialogTitle")

        self.employee_combo = QComboBox()
        for employee in employees:
            self.employee_combo.addItem(employee.name, employee.id)
        self.type_combo = QComboBox()
        for value, label in LEAVE_TYPE_NAMES.items():
            self.type_combo.addItem(label, value)

        self.start_date_edit = self._date_edit()
        self.end_date_edit = self._date_edit()
        today = QDate.currentDate()
        self.start_date_edit.setDate(today)
        self.end_date_edit.setDate(today)
        self.start_date_edit.dateChanged.connect(self._keep_end_after_start)

        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Opcional — máximo de 500 caracteres")
        self.notes_edit.setMaximumHeight(92)

        if leave is not None:
            employee_index = self.employee_combo.findData(
                leave.employee_id, Qt.ItemDataRole.UserRole
            )
            self.employee_combo.setCurrentIndex(employee_index)
            type_index = self.type_combo.findData(leave.type, Qt.ItemDataRole.UserRole)
            self.type_combo.setCurrentIndex(type_index)
            self.start_date_edit.setDate(
                QDate(
                    leave.start_date.year, leave.start_date.month, leave.start_date.day
                )
            )
            self.end_date_edit.setDate(
                QDate(leave.end_date.year, leave.end_date.month, leave.end_date.day)
            )
            self.notes_edit.setPlainText(leave.notes or "")

        form = QFormLayout()
        form.setSpacing(10)
        form.addRow("Funcionário:", self.employee_combo)
        form.addRow("Tipo:", self.type_combo)
        form.addRow("Data inicial:", self.start_date_edit)
        form.addRow("Data final:", self.end_date_edit)
        form.addRow("Observação:", self.notes_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Save
        )
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
        save_button.setText("Salvar")
        save_button.setObjectName("primaryButton")
        save_button.setEnabled(bool(employees))
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(16)
        layout.addWidget(heading)
        layout.addLayout(form)
        layout.addWidget(buttons)

    @staticmethod
    def _date_edit() -> QDateEdit:
        editor = QDateEdit()
        editor.setCalendarPopup(True)
        editor.setDisplayFormat("dd/MM/yyyy")
        editor.setMinimumDate(QDate(1900, 1, 1))
        editor.setMaximumDate(QDate(2200, 12, 31))
        return editor

    def _keep_end_after_start(self, selected: QDate) -> None:
        self.end_date_edit.setMinimumDate(selected)
        if self.end_date_edit.date() < selected:
            self.end_date_edit.setDate(selected)

    def employee_id(self) -> int:
        return int(self.employee_combo.currentData(Qt.ItemDataRole.UserRole))

    def leave_type(self) -> str:
        return str(self.type_combo.currentData(Qt.ItemDataRole.UserRole))

    def start_date(self) -> date:
        return self._to_date(self.start_date_edit.date())

    def end_date(self) -> date:
        return self._to_date(self.end_date_edit.date())

    def notes(self) -> str:
        return self.notes_edit.toPlainText()

    @staticmethod
    def _to_date(value: QDate) -> date:
        return date(value.year(), value.month(), value.day())
