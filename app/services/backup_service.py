from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from app.database.connection import Database
from app.database.repositories.schedule_repository import VALID_STATUSES


class BackupValidationError(ValueError):
    pass


class BackupService:
    FORMAT_VERSION = 1

    def __init__(self, database: Database) -> None:
        self.database = database

    def create_database_backup(self, destination: Path) -> None:
        if destination.resolve() == self.database.path.resolve():
            raise ValueError("Escolha um arquivo diferente do banco em uso.")
        self.database.backup_to(destination)

    def export_json(self, destination: Path) -> None:
        with self.database.connection() as connection:
            employees = [
                dict(row)
                for row in connection.execute(
                    "SELECT id, name FROM employees ORDER BY id"
                ).fetchall()
            ]
            entries = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT id, employee_id, date, status, notes
                    FROM schedule_entries ORDER BY id
                    """
                ).fetchall()
            ]
            settings = {
                row["key"]: row["value"]
                for row in connection.execute(
                    "SELECT key, value FROM settings ORDER BY key"
                ).fetchall()
            }

        payload = {
            "format": "ajusta-time-backup",
            "version": self.FORMAT_VERSION,
            "exported_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "employees": employees,
            "schedule_entries": entries,
            "settings": settings,
        }
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def import_json(self, source: Path) -> None:
        try:
            raw_payload = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise BackupValidationError("O arquivo JSON não pôde ser lido.") from error

        employees, entries, settings = self._validate_payload(raw_payload)
        with self.database.transaction() as connection:
            connection.execute("DELETE FROM schedule_entries")
            connection.execute("DELETE FROM employees")
            connection.execute("DELETE FROM settings")
            connection.executemany(
                "INSERT INTO employees(id, name) VALUES (?, ?)",
                ((item["id"], item["name"]) for item in employees),
            )
            connection.executemany(
                """
                INSERT INTO schedule_entries(id, employee_id, date, status, notes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    (
                        item["id"],
                        item["employee_id"],
                        item["date"],
                        item["status"],
                        item["notes"],
                    )
                    for item in entries
                ),
            )
            connection.executemany(
                "INSERT INTO settings(key, value) VALUES (?, ?)", settings.items()
            )
            connection.execute(
                """
                INSERT INTO settings(key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                ("demo_data_initialized", "1"),
            )

    def _validate_payload(
        self, payload: object
    ) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, str]]:
        if not isinstance(payload, dict):
            raise BackupValidationError("A raiz do backup deve ser um objeto JSON.")
        if payload.get("format") != "ajusta-time-backup":
            raise BackupValidationError("O arquivo não é um backup do Ajusta Time.")
        if payload.get("version") != self.FORMAT_VERSION:
            raise BackupValidationError("Versão de backup não suportada.")

        employees_raw = payload.get("employees")
        entries_raw = payload.get("schedule_entries")
        settings_raw = payload.get("settings")
        if not isinstance(employees_raw, list) or not isinstance(entries_raw, list):
            raise BackupValidationError("Funcionários ou ocorrências inválidos.")
        if not isinstance(settings_raw, dict):
            raise BackupValidationError("Configurações inválidas.")

        employees: list[dict[str, object]] = []
        employee_ids: set[int] = set()
        for item in employees_raw:
            if not isinstance(item, dict):
                raise BackupValidationError("Registro de funcionário inválido.")
            employee_id, name = item.get("id"), item.get("name")
            if (
                not isinstance(employee_id, int)
                or isinstance(employee_id, bool)
                or employee_id <= 0
                or not isinstance(name, str)
                or not name.strip()
                or employee_id in employee_ids
            ):
                raise BackupValidationError("Registro de funcionário inválido.")
            employee_ids.add(employee_id)
            employees.append({"id": employee_id, "name": name.strip()})

        entries: list[dict[str, object]] = []
        entry_ids: set[int] = set()
        employee_dates: set[tuple[int, str]] = set()
        for item in entries_raw:
            if not isinstance(item, dict):
                raise BackupValidationError("Registro de escala inválido.")
            entry_id = item.get("id")
            employee_id = item.get("employee_id")
            entry_date = item.get("date")
            status = item.get("status")
            notes = item.get("notes")
            if (
                not isinstance(entry_id, int)
                or isinstance(entry_id, bool)
                or entry_id <= 0
                or entry_id in entry_ids
                or not isinstance(employee_id, int)
                or isinstance(employee_id, bool)
                or employee_id not in employee_ids
                or not isinstance(entry_date, str)
                or status not in VALID_STATUSES
                or (notes is not None and not isinstance(notes, str))
            ):
                raise BackupValidationError("Registro de escala inválido.")
            try:
                parsed_date = date.fromisoformat(entry_date)
            except ValueError as error:
                raise BackupValidationError("Data de escala inválida.") from error
            if parsed_date.isoformat() != entry_date:
                raise BackupValidationError("A data deve usar o formato AAAA-MM-DD.")
            unique_key = (employee_id, entry_date)
            if unique_key in employee_dates:
                raise BackupValidationError("Há ocorrências duplicadas no backup.")
            entry_ids.add(entry_id)
            employee_dates.add(unique_key)
            entries.append(
                {
                    "id": entry_id,
                    "employee_id": employee_id,
                    "date": entry_date,
                    "status": status,
                    "notes": notes,
                }
            )

        settings: dict[str, str] = {}
        for key, value in settings_raw.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise BackupValidationError("Configuração inválida.")
            settings[key] = value
        return employees, entries, settings
