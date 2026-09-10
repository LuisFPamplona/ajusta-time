from __future__ import annotations

import calendar
from datetime import datetime

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPageLayout, QPageSize, QPainter, QPen
from PySide6.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PySide6.QtWidgets import QWidget

from app.database.repositories.employee_repository import Employee
from app.services.schedule_service import STATUS_LABELS

MONTH_NAMES = (
    "",
    "JANEIRO",
    "FEVEREIRO",
    "MARÇO",
    "ABRIL",
    "MAIO",
    "JUNHO",
    "JULHO",
    "AGOSTO",
    "SETEMBRO",
    "OUTUBRO",
    "NOVEMBRO",
    "DEZEMBRO",
)
WEEKDAY_NAMES = ("SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM")


class PrintService:
    def show_preview(
        self,
        parent: QWidget,
        year: int,
        month: int,
        employees: list[Employee],
        entries: dict[tuple[int, int], str],
        settings: dict[str, str],
    ) -> None:
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setPageOrientation(QPageLayout.Orientation.Landscape)
        printer.setFullPage(False)
        preview = QPrintPreviewDialog(printer, parent)
        preview.setWindowTitle("Pré-visualização da escala")
        preview.resize(1100, 760)
        preview.paintRequested.connect(
            lambda selected_printer: self.render(
                selected_printer, year, month, employees, entries, settings
            )
        )
        preview.exec()

    def render(
        self,
        printer: QPrinter,
        year: int,
        month: int,
        employees: list[Employee],
        entries: dict[tuple[int, int], str],
        settings: dict[str, str],
    ) -> None:
        painter = QPainter(printer)
        if not painter.isActive():
            raise RuntimeError("Não foi possível preparar a impressão.")
        try:
            page = printer.pageLayout().paintRectPixels(printer.resolution())
            page_rect = QRectF(page)
            self._render_pages(
                painter, printer, page_rect, year, month, employees, entries, settings
            )
        finally:
            painter.end()

    def _render_pages(
        self,
        painter: QPainter,
        printer: QPrinter,
        page: QRectF,
        year: int,
        month: int,
        employees: list[Employee],
        entries: dict[tuple[int, int], str],
        settings: dict[str, str],
    ) -> None:
        scale = printer.resolution() / 96.0
        margin = 18 * scale
        left, top = page.left() + margin, page.top() + margin
        width, height = page.width() - 2 * margin, page.height() - 2 * margin
        title_height = 75 * scale
        header_height = 42 * scale
        row_height = 25 * scale
        footer_height = 55 * scale
        body_height = height - title_height - header_height - footer_height
        rows_per_page = max(1, int(body_height // row_height))
        chunks = [
            employees[i : i + rows_per_page]
            for i in range(0, len(employees), rows_per_page)
        ] or [[]]

        for page_index, chunk in enumerate(chunks):
            if page_index:
                printer.newPage()
            y = top
            y = self._draw_title(
                painter,
                QRectF(left, y, width, title_height),
                year,
                month,
                settings,
            )
            y = self._draw_table(
                painter,
                QRectF(left, y, width, header_height + len(chunk) * row_height),
                year,
                month,
                chunk,
                entries,
                header_height,
                row_height,
                scale,
            )
            self._draw_footer(
                painter,
                QRectF(
                    left,
                    max(y + 8 * scale, top + height - footer_height),
                    width,
                    footer_height,
                ),
                settings,
                page_index + 1,
                len(chunks),
                scale,
            )

    def _draw_title(
        self,
        painter: QPainter,
        rect: QRectF,
        year: int,
        month: int,
        settings: dict[str, str],
    ) -> float:
        company = settings.get("company_name", "").strip()
        title = (
            settings.get("print_title", "Escala de Folgas").strip()
            or "Escala de Folgas"
        )
        painter.setPen(Qt.GlobalColor.black)
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        if company:
            painter.drawText(
                rect.adjusted(0, 0, 0, -rect.height() * 0.62),
                Qt.AlignmentFlag.AlignCenter,
                company.upper(),
            )
        painter.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        painter.drawText(
            rect.adjusted(0, rect.height() * 0.28, 0, -rect.height() * 0.28),
            Qt.AlignmentFlag.AlignCenter,
            title.upper(),
        )
        painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        painter.drawText(
            rect.adjusted(0, rect.height() * 0.62, 0, 0),
            Qt.AlignmentFlag.AlignCenter,
            f"{MONTH_NAMES[month]} / {year}",
        )
        return rect.bottom()

    def _draw_table(
        self,
        painter: QPainter,
        rect: QRectF,
        year: int,
        month: int,
        employees: list[Employee],
        entries: dict[tuple[int, int], str],
        header_height: float,
        row_height: float,
        scale: float,
    ) -> float:
        days = calendar.monthrange(year, month)[1]
        name_width = rect.width() * 0.19
        day_width = (rect.width() - name_width) / days
        thin_pen = QPen(Qt.GlobalColor.black, max(1.0, scale * 0.45))
        painter.setPen(thin_pen)
        painter.setFont(QFont("Arial", 6))

        painter.fillRect(
            QRectF(rect.left(), rect.top(), name_width, header_height),
            QColor("#d5d5d5"),
        )
        painter.drawRect(QRectF(rect.left(), rect.top(), name_width, header_height))
        painter.drawText(
            QRectF(rect.left(), rect.top(), name_width, header_height),
            Qt.AlignmentFlag.AlignCenter,
            "FUNCIONÁRIO",
        )
        for day in range(1, days + 1):
            x = rect.left() + name_width + (day - 1) * day_width
            weekday = calendar.weekday(year, month, day)
            cell = QRectF(x, rect.top(), day_width, header_height)
            weekend_color = QColor("#c9c9c9") if weekday >= 5 else QColor("#e5e5e5")
            painter.fillRect(cell, weekend_color)
            painter.drawRect(cell)
            painter.drawText(
                cell,
                Qt.AlignmentFlag.AlignCenter,
                f"{day:02d}\n{WEEKDAY_NAMES[weekday]}",
            )

        painter.setFont(QFont("Arial", 6))
        for row, employee in enumerate(employees):
            y = rect.top() + header_height + row * row_height
            name_cell = QRectF(rect.left(), y, name_width, row_height)
            painter.drawRect(name_cell)
            painter.drawText(
                name_cell.adjusted(4 * scale, 0, -2 * scale, 0),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                employee.name,
            )
            for day in range(1, days + 1):
                x = rect.left() + name_width + (day - 1) * day_width
                weekday = calendar.weekday(year, month, day)
                cell = QRectF(x, y, day_width, row_height)
                if weekday >= 5:
                    painter.fillRect(cell, QColor("#eeeeee"))
                painter.drawRect(cell)
                status = entries.get((employee.id, day))
                if status:
                    painter.setFont(QFont("Arial", 6, QFont.Weight.Bold))
                    painter.drawText(
                        cell, Qt.AlignmentFlag.AlignCenter, STATUS_LABELS[status]
                    )
                    painter.setFont(QFont("Arial", 6))
        return rect.top() + header_height + len(employees) * row_height

    def _draw_footer(
        self,
        painter: QPainter,
        rect: QRectF,
        settings: dict[str, str],
        page_number: int,
        page_count: int,
        scale: float,
    ) -> None:
        painter.setPen(Qt.GlobalColor.black)
        painter.setFont(QFont("Arial", 7))
        y = rect.top()
        if settings.get("show_legend", "1") == "1":
            painter.drawText(
                QRectF(rect.left(), y, rect.width(), 16 * scale),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                "F = Folga    FE = Férias    AT = Atestado    FA = Falta",
            )
            y += 18 * scale
        if settings.get("show_signature", "1") == "1":
            painter.drawText(
                QRectF(rect.left(), y, rect.width() * 0.7, 18 * scale),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                "Responsável: __________________________________________",
            )
        right_lines = [f"Página {page_number}/{page_count}"]
        if settings.get("show_print_date", "1") == "1":
            right_lines.insert(0, f"Impresso em {datetime.now().astimezone():%d/%m/%Y}")
        painter.drawText(
            QRectF(
                rect.left() + rect.width() * 0.7,
                y,
                rect.width() * 0.3,
                28 * scale,
            ),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            "\n".join(right_lines),
        )
