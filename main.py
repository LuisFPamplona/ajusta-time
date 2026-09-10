from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from app.database.connection import Database
from app.database.schema import initialize_database
from app.logging_config import configure_logging, install_exception_handler
from app.paths import get_database_path, get_log_dir, migrate_legacy_database
from app.ui.main_window import MainWindow
from app.ui.theme import apply_app_theme
from app.version import APP_NAME, APP_VERSION


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(APP_NAME)
    apply_app_theme(app)

    try:
        logger = configure_logging(get_log_dir())
        install_exception_handler(logger)
        logger.info("Inicializando %s versão %s.", APP_NAME, APP_VERSION)
        path = get_database_path()
        migrate_legacy_database(path)
        database = Database(path)
        initialize_database(database)
        window = MainWindow(database)
        window.show()
        logger.info("Aplicativo inicializado com sucesso.")
        return app.exec()
    except Exception:  # pragma: no cover
        logging.getLogger("ajusta_time").exception(
            "Falha durante a inicialização do aplicativo."
        )
        QMessageBox.critical(
            None,
            APP_NAME,
            "Não foi possível iniciar o aplicativo. Consulte o arquivo de log "
            "para obter mais detalhes.",
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
