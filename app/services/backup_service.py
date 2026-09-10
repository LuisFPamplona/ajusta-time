from __future__ import annotations

import json
from datetime import date, datetime
from os import replace
from pathlib import Path
from tempfile import NamedTemporaryFile

from app.database.connection import Database
from app.database.repositories.leave_repository import VALID_LEAVE_TYPES
from app.database.repositories.schedule_repository import VALID_SOURCES, VALID_STATUSES


class BackupValidationError(ValueError):
    pass


class BackupService:
    FORMAT_VERSION = 2
    SUPPORTED_VERSIONS = frozenset({1, 2})

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
                    """
                    SELECT id, name, default_day_off
                    FROM employees ORDER BY id
                    """
                ).fetchall()
            ]
            leave_periods = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT id, employee_id, type, start_date, end_date, notes
                    FROM leave_periods ORDER BY id
                    """
                ).fetchall()
            ]
            entries = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT
                        id, employee_id, date, status, source, notes,
                        leave_period_id
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
            "leave_periods": leave_periods,
            "schedule_entries": entries,
            "settings": settings,
        }
        self._write_json_atomically(destination, payload)

    def import_json(self, source: Path) -> None:
        try:
            raw_payload = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise BackupValidationError("O arquivo JSON não pôde ser lido.") from error

        employees, leave_periods, entries, settings = self._validate_payload(
            raw_payload
        )
        with self.database.transaction() as connection:
            connection.execute("DELETE FROM schedule_entries")
            connection.execute("DELETE FROM leave_periods")
            connection.execute("DELETE FROM employees")
            connection.execute("DELETE FROM settings")
            connection.executemany(
                """
                INSERT INTO employees(id, name, default_day_off)
                VALUES (?, ?, ?)
                """,
                (
                    (item["id"], item["name"], item["default_day_off"])
                    for item in employees
                ),
            )
            connection.executemany(
                """
                INSERT INTO leave_periods(
                    id, employee_id, type, start_date, end_date, notes
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    (
                        item["id"],
                        item["employee_id"],
                        item["type"],
                        item["start_date"],
                        item["end_date"],
                        item["notes"],
                    )
                    for item in leave_periods
                ),
            )
            connection.executemany(
                """
                INSERT INTO schedule_entries(
                    id, employee_id, date, status, source, notes, leave_period_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    (
                        item["id"],
                        item["employee_id"],
                        item["date"],
                        item["status"],
                        item["source"],
                        item["notes"],
                        item["leave_period_id"],
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
    ) -> tuple[
        list[dict[str, object]],
        list[dict[str, object]],
        list[dict[str, object]],
        dict[str, str],
    ]:
        if not isinstance(payload, dict):
            raise BackupValidationError("A raiz do backup deve ser um objeto JSON.")
        if payload.get("format") != "ajusta-time-backup":
            raise BackupValidationError("O arquivo não é um backup do Ajusta Time.")
        if payload.get("version") not in self.SUPPORTED_VERSIONS:
            raise BackupValidationError("Versão de backup não suportada.")

        employees_raw = payload.get("employees")
        leave_periods_raw = payload.get("leave_periods", [])
        entries_raw = payload.get("schedule_entries")
        settings_raw = payload.get("settings")
        if (
            not isinstance(employees_raw, list)
            or not isinstance(leave_periods_raw, list)
            or not isinstance(entries_raw, list)
        ):
            raise BackupValidationError("Funcionários ou ocorrências inválidos.")
        if not isinstance(settings_raw, dict):
            raise BackupValidationError("Configurações inválidas.")

        employees: list[dict[str, object]] = []
        employee_ids: set[int] = set()
        for item in employees_raw:
            if not isinstance(item, dict):
                raise BackupValidationError("Registro de funcionário inválido.")
            employee_id, name = item.get("id"), item.get("name")
            default_day_off = item.get("default_day_off")
            if (
                not isinstance(employee_id, int)
                or isinstance(employee_id, bool)
                or employee_id <= 0
                or not isinstance(name, str)
                or not name.strip()
                or employee_id in employee_ids
                or (
                    default_day_off is not None
                    and (
                        not isinstance(default_day_off, int)
                        or isinstance(default_day_off, bool)
                        or not 0 <= default_day_off <= 6
                    )
                )
            ):
                raise BackupValidationError("Registro de funcionário inválido.")
            employee_ids.add(employee_id)
            employees.append(
                {
                    "id": employee_id,
                    "name": name.strip(),
                    "default_day_off": default_day_off,
                }
            )

        leave_periods: list[dict[str, object]] = []
        leave_ids: set[int] = set()
        employee_periods: dict[int, list[tuple[date, date]]] = {}
        for item in leave_periods_raw:
            if not isinstance(item, dict):
                raise BackupValidationError("Registro de afastamento inválido.")
            leave_id = item.get("id")
            employee_id = item.get("employee_id")
            leave_type = item.get("type")
            start_date = item.get("start_date")
            end_date = item.get("end_date")
            notes = item.get("notes")
            if (
                not isinstance(leave_id, int)
                or isinstance(leave_id, bool)
                or leave_id <= 0
                or leave_id in leave_ids
                or not isinstance(employee_id, int)
                or isinstance(employee_id, bool)
                or employee_id not in employee_ids
                or leave_type not in VALID_LEAVE_TYPES
                or not isinstance(start_date, str)
                or not isinstance(end_date, str)
                or (notes is not None and not isinstance(notes, str))
            ):
                raise BackupValidationError("Registro de afastamento inválido.")
            try:
                parsed_start = date.fromisoformat(start_date)
                parsed_end = date.fromisoformat(end_date)
            except ValueError as error:
                raise BackupValidationError("Data de afastamento inválida.") from error
            if (
                parsed_start.isoformat() != start_date
                or parsed_end.isoformat() != end_date
                or parsed_start > parsed_end
            ):
                raise BackupValidationError("Período de afastamento inválido.")
            periods = employee_periods.setdefault(employee_id, [])
            if any(
                parsed_start <= existing_end and parsed_end >= existing_start
                for existing_start, existing_end in periods
            ):
                raise BackupValidationError("Há afastamentos sobrepostos no backup.")
            periods.append((parsed_start, parsed_end))
            leave_ids.add(leave_id)
            leave_periods.append(
                {
                    "id": leave_id,
                    "employee_id": employee_id,
                    "type": leave_type,
                    "start_date": start_date,
                    "end_date": end_date,
                    "notes": notes,
                }
            )

        leave_by_id = {item["id"]: item for item in leave_periods}
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
            source = item.get("source", "MANUAL")
            notes = item.get("notes")
            leave_period_id = item.get("leave_period_id")
            if (
                not isinstance(entry_id, int)
                or isinstance(entry_id, bool)
                or entry_id <= 0
                or entry_id in entry_ids
                or not isinstance(employee_id, int)
                or isinstance(employee_id, bool)
                or employee_id not in employee_ids
                or not isinstance(entry_date, str)
                or not isinstance(status, str)
                or status not in VALID_STATUSES
                or not isinstance(source, str)
                or source not in VALID_SOURCES
                or (source == "DEFAULT" and status != "DAY_OFF")
                or (status == "WORK_OVERRIDE" and source != "MANUAL")
                or (
                    source == "LEAVE"
                    and (
                        not isinstance(leave_period_id, int)
                        or isinstance(leave_period_id, bool)
                        or leave_period_id not in leave_ids
                        or status not in VALID_LEAVE_TYPES
                    )
                )
                or (source != "LEAVE" and leave_period_id is not None)
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
            if source == "LEAVE":
                period = leave_by_id[leave_period_id]
                if (
                    period["employee_id"] != employee_id
                    or period["type"] != status
                    or not period["start_date"] <= entry_date <= period["end_date"]
                ):
                    raise BackupValidationError(
                        "Ocorrência incompatível com o afastamento."
                    )
            entry_ids.add(entry_id)
            employee_dates.add(unique_key)
            entries.append(
                {
                    "id": entry_id,
                    "employee_id": employee_id,
                    "date": entry_date,
                    "status": status,
                    "source": source,
                    "notes": notes,
                    "leave_period_id": leave_period_id,
                }
            )

        leave_entries = {
            (item["leave_period_id"], item["date"])
            for item in entries
            if item["source"] == "LEAVE"
        }
        for period in leave_periods:
            current = date.fromisoformat(period["start_date"])
            end = date.fromisoformat(period["end_date"])
            while current <= end:
                if (period["id"], current.isoformat()) not in leave_entries:
                    raise BackupValidationError(
                        "O afastamento não possui todas as ocorrências diárias."
                    )
                current = date.fromordinal(current.toordinal() + 1)

        settings: dict[str, str] = {}
        for key, value in settings_raw.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise BackupValidationError("Configuração inválida.")
            settings[key] = value
        return employees, leave_periods, entries, settings

    @staticmethod
    def _write_json_atomically(destination: Path, payload: dict[str, object]) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=f".{destination.stem}-",
            suffix=".tmp",
            dir=destination.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            json.dump(payload, temporary, ensure_ascii=False, indent=2)
            temporary.write("\n")
        try:
            replace(temporary_path, destination)
        finally:
            temporary_path.unlink(missing_ok=True)
