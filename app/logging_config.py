from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from types import TracebackType

from PySide6.QtWidgets import QMessageBox

from app.version import APP_NAME

LOGGER_NAME = "ajusta_time"
logging.getLogger(LOGGER_NAME).addHandler(logging.NullHandler())


def configure_logging(log_directory: Path) -> logging.Logger:
    log_directory.mkdir(parents=True, exist_ok=True)
    log_path = (log_directory / "ajusta-time.log").resolve()
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    for handler in list(logger.handlers):
        if isinstance(handler, RotatingFileHandler):
            if Path(handler.baseFilename).resolve() == log_path:
                return logger
            logger.removeHandler(handler)
            handler.close()

    handler = RotatingFileHandler(
        log_path,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(handler)
    return logger


def install_exception_handler(logger: logging.Logger) -> None:
    previous_hook = sys.excepthook

    def handle_exception(
        exception_type: type[BaseException],
        exception: BaseException,
        traceback: TracebackType | None,
    ) -> None:
        if issubclass(exception_type, KeyboardInterrupt):
            previous_hook(exception_type, exception, traceback)
            return
        logger.critical(
            "Falha inesperada não tratada.",
            exc_info=(exception_type, exception, traceback),
        )
        QMessageBox.critical(
            None,
            APP_NAME,
            "Ocorreu um erro inesperado. Os detalhes foram registrados no log.",
        )

    sys.excepthook = handle_exception
