from __future__ import annotations

import calendar
from datetime import date

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.services.schedule_service import DailyScheduleSummary
from app.ui.icons import line_icon
from app.ui.theme import COLORS

WEEKDAY_NAMES = (
    "Segunda",
    "Terça",
    "Quarta",
    "Quinta",
    "Sexta",
    "Sábado",
    "Domingo",
)


class SummaryCard(QFrame):
    def __init__(self, icon_name: str, title: str, tone: str) -> None:
        super().__init__()
        self.setObjectName("summaryCard")
        self.setProperty("tone", tone)
        self.setMinimumHeight(82)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        tone_colors = {
            "blue": COLORS.primary,
            "red": COLORS.danger,
            "green": COLORS.success,
        }
        marker_label = QLabel()
        marker_label.setObjectName("cardMarker")
        marker_label.setProperty("tone", tone)
        marker_label.setPixmap(
            line_icon(icon_name, tone_colors[tone], 28).pixmap(28, 28)
        )
        marker_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        marker_label.setFixedWidth(44)

        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        self.value_label = QLabel()
        self.value_label.setObjectName("cardValue")
        self.detail_label = QLabel()
        self.detail_label.setObjectName("cardDetail")

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(1)
        text_layout.addWidget(title_label)
        value_row = QHBoxLayout()
        value_row.setContentsMargins(0, 0, 0, 0)
        value_row.setSpacing(8)
        value_row.addWidget(self.value_label)
        value_row.addWidget(self.detail_label, 1, Qt.AlignmentFlag.AlignBottom)
        text_layout.addLayout(value_row)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 11, 16, 11)
        layout.setSpacing(10)
        layout.addWidget(marker_label)
        layout.addLayout(text_layout, 1)

    def set_content(self, value: str, detail: str = "") -> None:
        self.value_label.setText(value)
        self.detail_label.setText(detail)
        self.detail_label.setVisible(bool(detail))


class CalendarDayWidget(QFrame):
    clicked = Signal(object)

    def __init__(
        self,
        displayed_date: date,
        current_month: bool,
        working_count: int = 0,
        unavailable_count: int = 0,
        is_maximum: bool = False,
        tooltip: str = "",
    ) -> None:
        super().__init__()
        self.displayed_date = displayed_date
        self.current_month = current_month
        state = (
            "external"
            if not current_month
            else "maximum"
            if is_maximum
            else "active"
            if unavailable_count
            else "empty"
        )
        self.setObjectName("calendarDay")
        self.setProperty("state", state)
        self.setMinimumSize(72, 54)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setFocusPolicy(
            Qt.FocusPolicy.StrongFocus if current_month else Qt.FocusPolicy.NoFocus
        )
        if current_month:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        if tooltip:
            self.setToolTip(tooltip)

        day_label = QLabel(str(displayed_date.day))
        day_label.setObjectName("dayNumber")
        day_label.setProperty("external", not current_month)
        if tooltip:
            day_label.setToolTip(tooltip)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 7, 10, 8)
        layout.setSpacing(2)
        layout.addWidget(day_label, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)
        if current_month:
            marker = "●  " if unavailable_count else ""
            employee_word = "funcionário" if working_count == 1 else "funcionários"
            count_label = QLabel(f"{marker}{working_count} {employee_word}")
            count_label.setObjectName("countPill")
            count_label.setProperty("state", state)
            count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if tooltip:
                count_label.setToolTip(tooltip)
            count_label.setSizePolicy(
                QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed
            )
            layout.addWidget(count_label, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if (
            self.current_month
            and event.button() == Qt.MouseButton.LeftButton
            and self.rect().contains(event.position().toPoint())
        ):
            self.clicked.emit(self.displayed_date)
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self.current_month and event.key() in (
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
            Qt.Key.Key_Space,
        ):
            self.clicked.emit(self.displayed_date)
            event.accept()
            return
        super().keyPressEvent(event)


class ScheduleCalendarWidget(QFrame):
    day_clicked = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("calendarSurface")
        self.day_widgets: dict[date, CalendarDayWidget] = {}
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(1, 1, 1, 1)
        self.grid.setHorizontalSpacing(1)
        self.grid.setVerticalSpacing(1)
        for column in range(7):
            self.grid.setColumnStretch(column, 1)

    def set_month(
        self,
        year: int,
        month: int,
        daily_summaries: dict[int, DailyScheduleSummary],
        maximum_day: int | None,
        month_name: str,
    ) -> None:
        self._clear()
        for column, weekday_name in enumerate(WEEKDAY_NAMES):
            label = QLabel(weekday_name)
            label.setObjectName("weekdayHeader")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid.addWidget(label, 0, column)

        weeks = calendar.Calendar(firstweekday=calendar.MONDAY).monthdatescalendar(
            year, month
        )
        for row, week in enumerate(weeks, start=1):
            self.grid.setRowStretch(row, 1)
            for column, displayed_date in enumerate(week):
                current_month = displayed_date.month == month
                summary = (
                    daily_summaries.get(displayed_date.day) if current_month else None
                )
                tooltip = ""
                if summary is not None:
                    lines = [
                        f"{displayed_date.day} de {month_name.lower()} de {year}",
                        "",
                        f"Folga: {summary.day_off}",
                        f"Férias: {summary.vacation}",
                        f"Atestado: {summary.medical_leave}",
                    ]
                    if summary.absence:
                        lines.append(f"Falta: {summary.absence}")
                    tooltip = "\n".join(lines)
                day_widget = CalendarDayWidget(
                    displayed_date,
                    current_month,
                    summary.working if summary is not None else 0,
                    summary.unavailable if summary is not None else 0,
                    current_month
                    and displayed_date.day == maximum_day
                    and summary is not None
                    and bool(summary.day_off),
                    tooltip,
                )
                day_widget.clicked.connect(self.day_clicked.emit)
                self.grid.addWidget(day_widget, row, column)
                self.day_widgets[displayed_date] = day_widget

    def _clear(self) -> None:
        self.day_widgets.clear()
        while item := self.grid.takeAt(0):
            if widget := item.widget():
                widget.deleteLater()
        for row in range(8):
            self.grid.setRowStretch(row, 0)
