from __future__ import annotations

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
QComboBox::drop-down {
    border: 0;
    width: 28px;
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
