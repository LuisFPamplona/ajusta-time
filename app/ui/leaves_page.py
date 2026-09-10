from __future__ import annotations

from datetime import date, datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
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

from app.database.repositories.leave_repository import LeavePeriod
from app.services.employee_service import EmployeeService
from app.services.leave_service import (
    LEAVE_TYPE_NAMES,
    LeaveConflictError,
    LeaveOverlapError,
    LeaveService,
)
from app.ui.leave_dialog import LeaveDialog


class LeavesPage(QWidget):
    leaves_changed = Signal()

    def __init__(
        self,
        employee_service: EmployeeService,
        leave_service: LeaveService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.employee_service = employee_service
        self.leave_service = leave_service

        title = QLabel("Afastamentos")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Gerencie férias e atestados dos funcionários.")
        subtitle.setObjectName("pageSubtitle")

        self.add_button = QPushButton("Novo afastamento")
        self.add_button.setObjectName("primaryButton")
        self.add_button.clicked.connect(self.add_leave)

        heading = QVBoxLayout()
        heading.setContentsMargins(0, 0, 0, 0)
        heading.setSpacing(2)
        heading.addWidget(title)
        heading.addWidget(subtitle)
        top_row = QHBoxLayout()
        top_row.addLayout(heading, 1)
        top_row.addWidget(self.add_button)

        self.employee_filter = QComboBox()
        self.employee_filter.setMinimumWidth(210)
        self.type_filter = QComboBox()
        self.type_filter.addItem("Todos", None)
        for value, label in LEAVE_TYPE_NAMES.items():
            self.type_filter.addItem(label, value)
        self.employee_filter.currentIndexChanged.connect(self.reload_table)
        self.type_filter.currentIndexChanged.connect(self.reload_table)

        filters = QHBoxLayout()
        filters.setSpacing(10)
        filters.addWidget(QLabel("Funcionário:"))
        filters.addWidget(self.employee_filter)
        filters.addWidget(QLabel("Tipo:"))
        filters.addWidget(self.type_filter)
        filters.addStretch()

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            [
                "Funcionário",
                "Tipo",
                "Início",
                "Fim",
                "Dias",
                "Situação",
                "Observação",
                "Ações",
            ]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)
        header = self.table.horizontalHeader()
        for column in (0, 6):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)
        for column in (1, 2, 3, 4, 5, 7):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self.table.doubleClicked.connect(self.edit_selected)

        self.empty_label = QLabel("Nenhum afastamento encontrado.")
        self.empty_label.setObjectName("emptyState")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 22, 30, 24)
        layout.setSpacing(13)
        layout.addLayout(top_row)
        layout.addLayout(filters)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.empty_label)
        self.reload()

    def reload(self) -> None:
        selected_employee = self.employee_filter.currentData(Qt.ItemDataRole.UserRole)
        employees = self.employee_service.list_employees()
        self.employee_filter.blockSignals(True)
        self.employee_filter.clear()
        self.employee_filter.addItem("Todos", None)
        for employee in employees:
            self.employee_filter.addItem(employee.name, employee.id)
        index = self.employee_filter.findData(
            selected_employee, Qt.ItemDataRole.UserRole
        )
        self.employee_filter.setCurrentIndex(max(0, index))
        self.employee_filter.blockSignals(False)
        self.add_button.setEnabled(bool(employees))
        self.add_button.setToolTip(
            "" if employees else "Cadastre um funcionário antes de criar afastamentos."
        )
        self.reload_table()

    def reload_table(self) -> None:
        employee_id = self.employee_filter.currentData(Qt.ItemDataRole.UserRole)
        leave_type = self.type_filter.currentData(Qt.ItemDataRole.UserRole)
        leaves = self.leave_service.list_leaves(employee_id, leave_type)
        self.table.setRowCount(len(leaves))
        today = datetime.now().astimezone().date()
        for row, leave in enumerate(leaves):
            employee_item = QTableWidgetItem(leave.employee_name)
            employee_item.setData(Qt.ItemDataRole.UserRole, leave.id)
            self.table.setItem(row, 0, employee_item)
            self.table.setCellWidget(
                row,
                1,
                self._badge(LEAVE_TYPE_NAMES[leave.type], leave.type.lower()),
            )
            self.table.setItem(
                row, 2, QTableWidgetItem(leave.start_date.strftime("%d/%m/%Y"))
            )
            self.table.setItem(
                row, 3, QTableWidgetItem(leave.end_date.strftime("%d/%m/%Y"))
            )
            day_word = "dia" if leave.days == 1 else "dias"
            self.table.setItem(row, 4, QTableWidgetItem(f"{leave.days} {day_word}"))
            status_text, status_kind = self._status(leave, today)
            self.table.setCellWidget(row, 5, self._badge(status_text, status_kind))
            self.table.setItem(row, 6, QTableWidgetItem(leave.notes or "—"))
            self.table.setCellWidget(row, 7, self._actions(leave.id))
        self.empty_label.setVisible(not leaves)
        self.table.setVisible(bool(leaves))

    def add_leave(self) -> None:
        employees = self.employee_service.list_employees()
        if not employees:
            QMessageBox.information(
                self,
                "Afastamentos",
                "Cadastre um funcionário antes de criar um afastamento.",
            )
            return
        dialog = LeaveDialog(employees, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if self._save(dialog):
            self.reload_table()
            self.leaves_changed.emit()

    def edit_selected(self) -> None:
        leave_id = self._selected_leave_id()
        if leave_id is None:
            QMessageBox.information(
                self, "Afastamentos", "Selecione um afastamento para editar."
            )
            return
        self.edit_leave(leave_id)

    def edit_leave(self, leave_id: int) -> None:
        try:
            leave = self.leave_service.get_leave(leave_id)
        except LookupError as error:
            QMessageBox.warning(self, "Afastamentos", str(error))
            self.reload_table()
            return
        dialog = LeaveDialog(
            self.employee_service.list_employees(), leave=leave, parent=self
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if self._save(dialog, leave_id):
            self.reload_table()
            self.leaves_changed.emit()

    def delete_leave(self, leave_id: int) -> None:
        try:
            leave = self.leave_service.get_leave(leave_id)
        except LookupError as error:
            QMessageBox.warning(self, "Afastamentos", str(error))
            self.reload_table()
            return
        answer = QMessageBox.question(
            self,
            "Excluir afastamento",
            f"Excluir {LEAVE_TYPE_NAMES[leave.type].lower()} de "
            f"{leave.employee_name}\n"
            f"{leave.start_date:%d/%m/%Y} até {leave.end_date:%d/%m/%Y}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.leave_service.delete_leave(leave_id)
        except (ValueError, LookupError) as error:
            QMessageBox.warning(self, "Afastamentos", str(error))
            return
        self.reload_table()
        self.leaves_changed.emit()

    def _save(self, dialog: LeaveDialog, leave_id: int | None = None) -> bool:
        replace_conflicts = False
        while True:
            try:
                if leave_id is None:
                    self.leave_service.create_leave(
                        dialog.employee_id(),
                        dialog.leave_type(),
                        dialog.start_date(),
                        dialog.end_date(),
                        dialog.notes(),
                        replace_conflicts,
                    )
                else:
                    self.leave_service.update_leave(
                        leave_id,
                        dialog.employee_id(),
                        dialog.leave_type(),
                        dialog.start_date(),
                        dialog.end_date(),
                        dialog.notes(),
                        replace_conflicts,
                    )
                return True
            except LeaveConflictError as error:
                if not self._confirm_conflict(error):
                    return False
                replace_conflicts = True
            except (LeaveOverlapError, TypeError, ValueError, LookupError) as error:
                QMessageBox.warning(self, "Afastamentos", str(error))
                return False
            except Exception as error:  # noqa: BLE001 - limite da interface gráfica
                QMessageBox.critical(
                    self,
                    "Afastamentos",
                    f"Não foi possível salvar o afastamento.\n\n{error}",
                )
                return False

    def _confirm_conflict(self, error: LeaveConflictError) -> bool:
        details = "\n".join(
            f"{entry.date:%d/%m/%Y} — {self._entry_name(entry.status)}"
            for entry in error.conflicts[:8]
        )
        if len(error.conflicts) > 8:
            details += f"\n… e mais {len(error.conflicts) - 8} ocorrência(s)."
        message = QMessageBox(self)
        message.setIcon(QMessageBox.Icon.Warning)
        message.setWindowTitle("Conflito no período")
        message.setText(
            f"Existem {len(error.conflicts)} ocorrências já cadastradas nesse "
            "período. Deseja substituí-las pelo afastamento?"
        )
        message.setInformativeText(details)
        replace_button = message.addButton(
            "Substituir", QMessageBox.ButtonRole.AcceptRole
        )
        message.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        message.exec()
        return message.clickedButton() is replace_button

    def _actions(self, leave_id: int) -> QWidget:
        edit_button = QPushButton("Editar")
        delete_button = QPushButton("Excluir")
        edit_button.setProperty("compact", True)
        delete_button.setProperty("compact", True)
        edit_button.clicked.connect(lambda: self.edit_leave(leave_id))
        delete_button.clicked.connect(lambda: self.delete_leave(leave_id))
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 3, 4, 3)
        layout.setSpacing(5)
        layout.addWidget(edit_button)
        layout.addWidget(delete_button)
        return widget

    @staticmethod
    def _badge(text: str, kind: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("leaveBadge")
        label.setProperty("kind", kind)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setMargin(5)
        return label

    @staticmethod
    def _status(leave: LeavePeriod, today: date) -> tuple[str, str]:
        if leave.start_date > today:
            return "Agendado", "scheduled"
        if leave.end_date < today:
            return "Concluído", "completed"
        return "Em andamento", "active"

    @staticmethod
    def _entry_name(status: str) -> str:
        return {
            "DAY_OFF": "Folga manual",
            "WORK_OVERRIDE": "Trabalho normal",
            "VACATION": "Férias",
            "MEDICAL_LEAVE": "Atestado",
            "ABSENCE": "Falta",
        }.get(status, status)

    def _selected_leave_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0 or self.table.item(row, 0) is None:
            return None
        return int(self.table.item(row, 0).data(Qt.ItemDataRole.UserRole))
