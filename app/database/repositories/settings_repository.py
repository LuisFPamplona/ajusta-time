from __future__ import annotations

from app.database.connection import Database

DEFAULT_SETTINGS = {
    "company_name": "",
    "print_title": "Escala de Folgas",
    "show_legend": "1",
    "show_signature": "1",
    "show_print_date": "1",
}


class SettingsRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def get_all(self) -> dict[str, str]:
        with self.database.connection() as connection:
            rows = connection.execute("SELECT key, value FROM settings").fetchall()
        settings = DEFAULT_SETTINGS.copy()
        settings.update({row["key"]: row["value"] or "" for row in rows})
        return settings

    def save(self, settings: dict[str, str]) -> None:
        allowed = DEFAULT_SETTINGS.keys()
        with self.database.transaction() as connection:
            connection.executemany(
                """
                INSERT INTO settings(key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                ((key, settings[key]) for key in allowed if key in settings),
            )
