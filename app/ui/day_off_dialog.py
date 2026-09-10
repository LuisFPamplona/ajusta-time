from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.database.repositories.employee_repository import Employee
from app.services.schedule_service import STATUS_NAMES


class DayOffDialog(QDialog):
    def __init__(
        self,
        selected_date: date,
        month_name: str,
        employees: list[Employee],
        statuses: dict[int, str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(
            f"Folgas — {selected_date.day} de {month_name.lower()} de "
            f"{selected_date.year}"
        )
        self.setMinimumSize(520, 470)
        self.resize(560, 540)

        title = QLabel(self.windowTitle())
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "Marque os funcionários que estarão de folga. "
            "Outras ocorrências são preservadas."
        )
        subtitle.setObjectName("pageSubtitle")
        subtitle.setWordWrap(True)

        self.employee_list = QListWidget()
        self.employee_list.setAlternatingRowColors(True)
        for employee in employees:
            status = statuses.get(employee.id)
            text = employee.name
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, employee.id)
            if status == "DAY_OFF":
                item.setFlags(
                    Qt.ItemFlag.ItemIsEnabled
                    | Qt.ItemFlag.ItemIsSelectable
                    | Qt.ItemFlag.ItemIsUserCheckable
                )
                item.setCheckState(Qt.CheckState.Checked)
            elif status:
                item.setText(f"{employee.name} — {STATUS_NAMES[status]} (preservado)")
                item.setFlags(Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                item.setToolTip(
                    "Este funcionário já possui outra ocorrência nesta data."
                )
            else:
                item.setFlags(
                    Qt.ItemFlag.ItemIsEnabled
                    | Qt.ItemFlag.ItemIsSelectable
                    | Qt.ItemFlag.ItemIsUserCheckable
                )
                item.setCheckState(Qt.CheckState.Unchecked)
            self.employee_list.addItem(item)

        if not employees:
            empty_label = QLabel(
                "Nenhum funcionário cadastrado. Use a aba Funcionários para adicionar."
            )
            empty_label.setWordWrap(True)
        else:
            empty_label = None

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
        layout.setSpacing(10)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(4)
        if empty_label is not None:
            layout.addWidget(empty_label)
        layout.addWidget(self.employee_list, 1)
        layout.addWidget(buttons)

    def selected_employee_ids(self) -> set[int]:
        return {
            int(item.data(Qt.ItemDataRole.UserRole))
            for index in range(self.employee_list.count())
            if (item := self.employee_list.item(index)).checkState()
            == Qt.CheckState.Checked
        }
