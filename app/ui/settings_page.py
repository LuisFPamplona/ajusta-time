from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.database.repositories.settings_repository import SettingsRepository
from app.services.backup_service import BackupService


class SettingsPage(QWidget):
    data_imported = Signal()

    def __init__(
        self,
        settings_repository: SettingsRepository,
        backup_service: BackupService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.settings_repository = settings_repository
        self.backup_service = backup_service

        title = QLabel("Configurações")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Personalize a impressão e proteja os dados do aplicativo.")
        subtitle.setObjectName("pageSubtitle")

        self.company_name = QLineEdit()
        self.print_title = QLineEdit()
        self.show_legend = QCheckBox("Mostrar legenda")
        self.show_signature = QCheckBox("Mostrar assinatura")
        self.show_print_date = QCheckBox("Mostrar data de impressão")

        form = QFormLayout()
        form.addRow("Nome da empresa:", self.company_name)
        form.addRow("Título da impressão:", self.print_title)
        form.addRow("", self.show_legend)
        form.addRow("", self.show_signature)
        form.addRow("", self.show_print_date)
        save_button = QPushButton("Salvar configurações")
        save_button.clicked.connect(self.save_settings)
        form.addRow("", save_button)

        print_group = QGroupBox("Impressão")
        print_group.setLayout(form)

        sqlite_button = QPushButton("Backup do banco SQLite")
        export_button = QPushButton("Exportar JSON")
        import_button = QPushButton("Importar JSON")
        sqlite_button.clicked.connect(self.backup_database)
        export_button.clicked.connect(self.export_json)
        import_button.clicked.connect(self.import_json)
        backup_buttons = QHBoxLayout()
        backup_buttons.addWidget(sqlite_button)
        backup_buttons.addWidget(export_button)
        backup_buttons.addWidget(import_button)
        backup_buttons.addStretch()
        backup_group = QGroupBox("Backup e restauração")
        backup_layout = QVBoxLayout(backup_group)
        backup_layout.addWidget(
            QLabel(
                "O backup inclui funcionários, afastamentos, ocorrências e "
                "configurações."
            )
        )
        backup_layout.addLayout(backup_buttons)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(10)
        layout.addWidget(print_group)
        layout.addWidget(backup_group)
        layout.addStretch()
        self.reload()

    def reload(self) -> None:
        settings = self.settings_repository.get_all()
        self.company_name.setText(settings["company_name"])
        self.print_title.setText(settings["print_title"])
        self.show_legend.setChecked(settings["show_legend"] == "1")
        self.show_signature.setChecked(settings["show_signature"] == "1")
        self.show_print_date.setChecked(settings["show_print_date"] == "1")

    def save_settings(self) -> None:
        title = self.print_title.text().strip()
        if not title:
            QMessageBox.warning(self, "Configurações", "Informe o título da impressão.")
            return
        self.settings_repository.save(
            {
                "company_name": self.company_name.text().strip(),
                "print_title": title,
                "show_legend": "1" if self.show_legend.isChecked() else "0",
                "show_signature": "1" if self.show_signature.isChecked() else "0",
                "show_print_date": "1" if self.show_print_date.isChecked() else "0",
            }
        )
        QMessageBox.information(self, "Configurações", "Configurações salvas.")

    def backup_database(self) -> None:
        today = datetime.now().astimezone().date()
        default_name = f"backup-ajusta-time-{today:%Y-%m-%d}.db"
        filename, _ = QFileDialog.getSaveFileName(
            self, "Salvar backup SQLite", default_name, "Banco SQLite (*.db)"
        )
        if not filename:
            return
        try:
            self.backup_service.create_database_backup(Path(filename))
        except Exception as error:  # noqa: BLE001 - limite da interface gráfica
            QMessageBox.critical(
                self, "Backup", f"Não foi possível criar o backup.\n\n{error}"
            )
            return
        QMessageBox.information(self, "Backup", "Backup SQLite criado com sucesso.")

    def export_json(self) -> None:
        today = datetime.now().astimezone().date()
        default_name = f"backup-ajusta-time-{today:%Y-%m-%d}.json"
        filename, _ = QFileDialog.getSaveFileName(
            self, "Exportar backup JSON", default_name, "Arquivo JSON (*.json)"
        )
        if not filename:
            return
        destination = Path(filename)
        if destination.suffix.lower() != ".json":
            destination = destination.with_suffix(".json")
        try:
            self.backup_service.export_json(destination)
        except Exception as error:  # noqa: BLE001 - limite da interface gráfica
            QMessageBox.critical(
                self, "Backup", f"Não foi possível exportar o JSON.\n\n{error}"
            )
            return
        QMessageBox.information(self, "Backup", "Backup JSON exportado com sucesso.")

    def import_json(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self, "Importar backup JSON", "", "Arquivo JSON (*.json)"
        )
        if not filename:
            return
        answer = QMessageBox.warning(
            self,
            "Importar backup",
            "A importação substituirá todos os dados atuais. Deseja continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.backup_service.import_json(Path(filename))
        except Exception as error:  # noqa: BLE001 - limite da interface gráfica
            QMessageBox.critical(
                self, "Backup", f"Não foi possível importar o backup.\n\n{error}"
            )
            return
        self.reload()
        self.data_imported.emit()
        QMessageBox.information(self, "Backup", "Backup importado com sucesso.")
