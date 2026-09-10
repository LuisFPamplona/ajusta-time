from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.database.repositories.employee_repository import EmployeeHasScheduleError
from app.services.employee_service import EmployeeService
from app.ui.employee_dialog import DAY_OFF_NAMES, EmployeeDialog


class EmployeesPage(QWidget):
    employees_changed = Signal()

    def __init__(self, service: EmployeeService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.service = service

        title = QLabel("Funcionários")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Cadastre as pessoas que aparecerão na escala mensal.")
        subtitle.setObjectName("pageSubtitle")

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["ID", "Nome", "Folga padrão"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.doubleClicked.connect(self.edit_selected)

        add_button = QPushButton("Adicionar")
        edit_button = QPushButton("Editar")
        delete_button = QPushButton("Excluir")
        add_button.clicked.connect(self.add_employee)
        edit_button.clicked.connect(self.edit_selected)
        delete_button.clicked.connect(self.delete_selected)

        buttons = QHBoxLayout()
        buttons.addWidget(add_button)
        buttons.addWidget(edit_button)
        buttons.addWidget(delete_button)
        buttons.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(10)
        layout.addLayout(buttons)
        layout.addWidget(self.table)
        self.reload()

    def reload(self) -> None:
        employees = self.service.list_employees()
        self.table.setRowCount(len(employees))
        for row, employee in enumerate(employees):
            id_item = QTableWidgetItem(str(employee.id))
            id_item.setData(Qt.ItemDataRole.UserRole, employee.id)
            name_item = QTableWidgetItem(employee.name)
            name_item.setData(Qt.ItemDataRole.UserRole, employee.default_day_off)
            day_off_item = QTableWidgetItem(DAY_OFF_NAMES[employee.default_day_off])
            self.table.setItem(row, 0, id_item)
            self.table.setItem(row, 1, name_item)
            self.table.setItem(row, 2, day_off_item)

    def add_employee(self) -> None:
        dialog = EmployeeDialog("Adicionar funcionário", parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.service.add_employee(dialog.employee_name(), dialog.default_day_off())
        except ValueError as error:
            QMessageBox.warning(self, "Funcionários", str(error))
            return
        self.reload()
        self.employees_changed.emit()

    def edit_selected(self) -> None:
        selected = self._selected_employee()
        if selected is None:
            QMessageBox.information(
                self, "Funcionários", "Selecione um funcionário para editar."
            )
            return
        employee_id, current_name, default_day_off = selected
        dialog = EmployeeDialog(
            "Editar funcionário",
            current_name,
            default_day_off,
            self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.service.update_employee(
                employee_id,
                dialog.employee_name(),
                dialog.default_day_off(),
            )
        except (ValueError, LookupError) as error:
            QMessageBox.warning(self, "Funcionários", str(error))
            return
        self.reload()
        self.employees_changed.emit()

    def delete_selected(self) -> None:
        selected = self._selected_employee()
        if selected is None:
            QMessageBox.information(
                self, "Funcionários", "Selecione um funcionário para excluir."
            )
            return
        employee_id, name, _ = selected
        answer = QMessageBox.question(
            self,
            "Excluir funcionário",
            f"Deseja excluir {name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.service.delete_employee(employee_id)
        except EmployeeHasScheduleError as error:
            QMessageBox.warning(self, "Funcionários", str(error))
            return
        except LookupError as error:
            QMessageBox.warning(self, "Funcionários", str(error))
            return
        self.reload()
        self.employees_changed.emit()

    def _selected_employee(self) -> tuple[int, str, int | None] | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        default_day_off = self.table.item(row, 1).data(Qt.ItemDataRole.UserRole)
        return (
            int(self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)),
            self.table.item(row, 1).text(),
            int(default_day_off) if default_day_off is not None else None,
        )
