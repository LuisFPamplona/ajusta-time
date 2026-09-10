from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

DAY_OFF_OPTIONS: tuple[tuple[str, int | None], ...] = (
    ("Nenhuma", None),
    ("Segunda-feira", 0),
    ("Terça-feira", 1),
    ("Quarta-feira", 2),
    ("Quinta-feira", 3),
    ("Sexta-feira", 4),
    ("Sábado", 5),
    ("Domingo", 6),
)

DAY_OFF_NAMES = {value: label for label, value in DAY_OFF_OPTIONS}


class EmployeeDialog(QDialog):
    def __init__(
        self,
        title: str,
        name: str = "",
        default_day_off: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(440)

        heading = QLabel(title)
        heading.setObjectName("dialogTitle")
        self.name_edit = QLineEdit(name)
        self.name_edit.setPlaceholderText("Nome completo")
        self.name_edit.setMaxLength(150)
        self.day_off_combo = QComboBox()
        for label, value in DAY_OFF_OPTIONS:
            self.day_off_combo.addItem(label, value)
        selected_index = self.day_off_combo.findData(
            default_day_off, Qt.ItemDataRole.UserRole
        )
        self.day_off_combo.setCurrentIndex(max(0, selected_index))

        form = QFormLayout()
        form.setSpacing(10)
        form.addRow("Nome:", self.name_edit)
        form.addRow("Folga padrão:", self.day_off_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Save
        )
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
        save_button.setText("Salvar")
        save_button.setObjectName("primaryButton")
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(16)
        layout.addWidget(heading)
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.name_edit.selectAll()
        self.name_edit.setFocus()

    def employee_name(self) -> str:
        return self.name_edit.text()

    def default_day_off(self) -> int | None:
        value = self.day_off_combo.currentData(Qt.ItemDataRole.UserRole)
        return int(value) if value is not None else None
