from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


@dataclass(frozen=True, slots=True)
class ThemeColors:
    """Canonical colors for widgets, icons and native Qt popup surfaces."""

    background: str = "#f7f9fc"
    surface: str = "#ffffff"
    surface_muted: str = "#f1f3f7"
    surface_hover: str = "#f5f8fd"
    text: str = "#162033"
    text_muted: str = "#667085"
    text_disabled: str = "#98a2b3"
    border: str = "#cfd8e6"
    primary: str = "#1769e8"
    primary_hover: str = "#0d5edb"
    primary_soft: str = "#e4efff"
    danger: str = "#c92333"
    success: str = "#249b56"


COLORS = ThemeColors()


def build_app_palette() -> QPalette:
    palette = QPalette()
    standard_roles = {
        QPalette.ColorRole.Window: COLORS.background,
        QPalette.ColorRole.WindowText: COLORS.text,
        QPalette.ColorRole.Base: COLORS.surface,
        QPalette.ColorRole.AlternateBase: COLORS.background,
        QPalette.ColorRole.ToolTipBase: COLORS.surface,
        QPalette.ColorRole.ToolTipText: COLORS.text,
        QPalette.ColorRole.Text: COLORS.text,
        QPalette.ColorRole.Button: COLORS.surface,
        QPalette.ColorRole.ButtonText: COLORS.text,
        QPalette.ColorRole.BrightText: COLORS.surface,
        QPalette.ColorRole.Highlight: COLORS.primary,
        QPalette.ColorRole.HighlightedText: COLORS.surface,
        QPalette.ColorRole.PlaceholderText: COLORS.text_disabled,
        QPalette.ColorRole.Link: COLORS.primary,
    }
    for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive):
        for role, color in standard_roles.items():
            palette.setColor(group, role, QColor(color))
    for role in (
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
        QPalette.ColorRole.PlaceholderText,
    ):
        palette.setColor(
            QPalette.ColorGroup.Disabled, role, QColor(COLORS.text_disabled)
        )
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.Base,
        QColor(COLORS.surface_muted),
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.Button,
        QColor(COLORS.surface_muted),
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.Highlight,
        QColor(COLORS.border),
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.HighlightedText,
        QColor(COLORS.text_disabled),
    )
    return palette


def apply_app_theme(application: QApplication) -> None:
    """Force one light palette for native and styled widgets across platforms."""
    application.setStyle("Fusion")
    application.setPalette(build_app_palette())
    application.setStyleSheet(APP_STYLE_SHEET)


APP_STYLE_SHEET = """
QMainWindow, QWidget#appRoot {
    background: #f7f9fc;
}
QWidget {
    color: #162033;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 10pt;
}
QLabel#pageTitle {
    color: #111c2f;
    font-size: 22pt;
    font-weight: 700;
}
QLabel#pageSubtitle {
    color: #718096;
    font-size: 10.5pt;
}
QLabel#dialogTitle {
    color: #111c2f;
    font-size: 16pt;
    font-weight: 700;
}
QLabel#legend {
    color: #667085;
    padding: 5px 4px;
}
QTabWidget::pane {
    background: #f7f9fc;
    border: 0;
    border-top: 1px solid #dde4ee;
}
QTabBar {
    background: #ffffff;
}
QTabBar::tab {
    background: #ffffff;
    border: 0;
    border-right: 1px solid #e3e8f0;
    border-bottom: 3px solid transparent;
    color: #39465a;
    min-width: 155px;
    padding: 15px 22px 13px 22px;
}
QTabBar::tab:hover {
    background: #f8faff;
    color: #1769e8;
}
QTabBar::tab:selected {
    color: #1769e8;
    border-bottom: 3px solid #1769e8;
    font-weight: 600;
}
QPushButton {
    background: #ffffff;
    border: 1px solid #cfd8e6;
    border-radius: 7px;
    min-height: 24px;
    padding: 8px 15px;
}
QPushButton:hover {
    background: #f5f8fd;
    border-color: #9cadc5;
}
QPushButton:pressed {
    background: #eaf0f8;
}
QPushButton:disabled {
    background: #f1f3f7;
    border-color: #d9e1ec;
    color: #98a2b3;
}
QPushButton#primaryButton {
    background: #1769e8;
    border-color: #1769e8;
    color: #ffffff;
    font-weight: 600;
    padding-left: 20px;
    padding-right: 20px;
}
QPushButton#primaryButton:hover {
    background: #0d5edb;
}
QPushButton#navButton {
    font-size: 14pt;
    min-width: 20px;
    padding: 6px 9px;
}
QComboBox, QSpinBox, QLineEdit {
    background: #ffffff;
    border: 1px solid #cfd8e6;
    border-radius: 7px;
    min-height: 24px;
    padding: 7px 10px;
}
QComboBox:hover, QSpinBox:hover, QLineEdit:hover {
    border-color: #9cadc5;
}
QComboBox:disabled, QSpinBox:disabled, QLineEdit:disabled {
    background: #f1f3f7;
    border-color: #d9e1ec;
    color: #98a2b3;
}
QComboBox::drop-down {
    border: 0;
    width: 28px;
}
QComboBox QAbstractItemView, QComboBox QListView {
    background-color: #ffffff;
    alternate-background-color: #f7f9fc;
    border: 1px solid #cfd8e6;
    color: #162033;
    outline: 0;
    selection-background-color: #e4efff;
    selection-color: #162033;
}
QComboBox QAbstractItemView::item, QComboBox QListView::item {
    background-color: #ffffff;
    color: #162033;
    min-height: 28px;
    padding: 4px 8px;
}
QComboBox QAbstractItemView::item:hover,
QComboBox QAbstractItemView::item:selected,
QComboBox QListView::item:hover,
QComboBox QListView::item:selected {
    background-color: #e4efff;
    color: #162033;
}
QMenu {
    background-color: #ffffff;
    border: 1px solid #cfd8e6;
    color: #162033;
    padding: 5px;
}
QMenu::item {
    background-color: transparent;
    border-radius: 4px;
    color: #162033;
    padding: 7px 24px 7px 10px;
}
QMenu::item:selected {
    background-color: #e4efff;
    color: #162033;
}
QMenu::item:disabled {
    color: #98a2b3;
}
QMenu::separator {
    background: #e3e8f0;
    height: 1px;
    margin: 5px 8px;
}
QToolTip {
    background-color: #162033;
    border: 1px solid #39465a;
    color: #ffffff;
    padding: 5px 7px;
}
QFrame#summaryCard {
    background: #ffffff;
    border: 1px solid #dae2ed;
    border-radius: 9px;
}
QFrame#summaryCard[tone="blue"] {
    background: #eef6ff;
    border-color: #c8dfff;
}
QFrame#summaryCard[tone="red"] {
    background: #fff2f3;
    border-color: #f4cbd0;
}
QFrame#summaryCard[tone="green"] {
    background: #effaf3;
    border-color: #c5e8d0;
}
QLabel#cardMarker {
    font-size: 21pt;
    font-weight: 700;
}
QLabel#cardMarker[tone="blue"] { color: #1769e8; }
QLabel#cardMarker[tone="red"] { color: #d12c3b; }
QLabel#cardMarker[tone="green"] { color: #249b56; }
QLabel#cardTitle {
    color: #3c4759;
    font-size: 9.5pt;
}
QLabel#cardValue {
    color: #162033;
    font-size: 15pt;
    font-weight: 700;
}
QLabel#cardDetail {
    color: #718096;
    font-size: 9.5pt;
}
QFrame#calendarSurface {
    background: #d9e1ec;
    border: 1px solid #cdd7e4;
    border-radius: 10px;
}
QLabel#weekdayHeader {
    background: #edf2f8;
    color: #1d2939;
    font-weight: 600;
    padding: 9px 4px;
}
QFrame#calendarDay {
    background: #ffffff;
    border: 0;
}
QFrame#calendarDay[state="external"] {
    background: #fafbfd;
}
QFrame#calendarDay[state="active"]:hover,
QFrame#calendarDay[state="maximum"]:hover,
QFrame#calendarDay[state="empty"]:hover {
    background: #f4f8ff;
}
QLabel#dayNumber {
    color: #162033;
    font-size: 11pt;
    font-weight: 700;
}
QLabel#dayNumber[external="true"] {
    color: #b1bac8;
    font-weight: 500;
}
QLabel#countPill {
    border-radius: 12px;
    padding: 5px 9px;
}
QLabel#countPill[state="empty"] {
    background: #f1f3f7;
    color: #657187;
}
QLabel#countPill[state="active"] {
    background: #e3f0ff;
    color: #1264df;
    font-weight: 600;
}
QLabel#countPill[state="maximum"] {
    background: #ffe5e7;
    color: #c92333;
    font-weight: 700;
}
QTableWidget, QListWidget {
    background: #ffffff;
    border: 1px solid #d7dfe9;
    border-radius: 7px;
    gridline-color: #d7dfe9;
    alternate-background-color: #f8fafc;
    selection-background-color: #e4efff;
    selection-color: #162033;
}
QHeaderView::section {
    background: #edf2f8;
    border: 0;
    border-right: 1px solid #d7dfe9;
    border-bottom: 1px solid #d7dfe9;
    font-weight: 600;
    padding: 7px;
}
QListWidget::item {
    border-bottom: 1px solid #edf0f5;
    padding: 9px 7px;
}
QListWidget::item:disabled {
    color: #8993a3;
    background: #f7f8fa;
}
QGroupBox {
    background: #ffffff;
    border: 1px solid #d9e1ec;
    border-radius: 8px;
    font-weight: 600;
    margin-top: 12px;
    padding: 14px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 5px;
}
QDialog {
    background: #f7f9fc;
}
"""
