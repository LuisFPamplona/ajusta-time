from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from app.database.connection import Database
from app.database.schema import initialize_database
from app.paths import database_path
from app.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Ajusta Time")
    app.setOrganizationName("Ajusta Time")

    try:
        database = Database(database_path())
        initialize_database(database)
        window = MainWindow(database)
        window.show()
        return app.exec()
    except Exception as error:  # noqa: BLE001  # pragma: no cover
        QMessageBox.critical(
            None,
            "Ajusta Time",
            f"Não foi possível iniciar o aplicativo.\n\n{error}",
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
