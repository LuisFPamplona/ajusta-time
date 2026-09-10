from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from os import replace
from pathlib import Path
from tempfile import NamedTemporaryFile

logger = logging.getLogger("ajusta_time.database")


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            yield connection
        except sqlite3.Error:
            logger.exception("Falha inesperada em operação SQLite.")
            raise
        finally:
            connection.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN")
            yield connection
            connection.commit()
        except sqlite3.IntegrityError:
            connection.rollback()
            raise
        except sqlite3.Error:
            connection.rollback()
            logger.exception("Falha inesperada em transação SQLite; rollback aplicado.")
            raise
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def backup_to(self, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.resolve() == self.path.resolve():
            raise ValueError("O destino do backup deve ser diferente do banco em uso.")
        with NamedTemporaryFile(
            prefix=f".{destination.stem}-",
            suffix=".tmp",
            dir=destination.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
        try:
            with (
                closing(self.connect()) as source,
                closing(sqlite3.connect(temporary_path)) as target,
            ):
                source.backup(target)
                if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise sqlite3.DatabaseError("O backup não passou na integridade.")
            replace(temporary_path, destination)
        finally:
            temporary_path.unlink(missing_ok=True)
