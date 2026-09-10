from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap


def line_icon(name: str, color: str = "#526078", size: int = 22) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), 1.8)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    if name == "calendar":
        painter.drawRoundedRect(QRectF(3.5, 4.5, 15, 14), 2, 2)
        painter.drawLine(QPointF(4, 8.5), QPointF(18, 8.5))
        painter.drawLine(QPointF(7, 2.8), QPointF(7, 6.2))
        painter.drawLine(QPointF(15, 2.8), QPointF(15, 6.2))
    elif name == "users":
        painter.drawEllipse(QPointF(11, 7), 3, 3)
        painter.drawArc(QRectF(5.5, 11, 11, 8), 0, 180 * 16)
        painter.drawEllipse(QPointF(4.5, 9), 2, 2)
        painter.drawEllipse(QPointF(17.5, 9), 2, 2)
        painter.drawArc(QRectF(0.8, 12.5, 7, 6), 0, 155 * 16)
        painter.drawArc(QRectF(14.2, 12.5, 7, 6), 25 * 16, 155 * 16)
    elif name == "settings":
        painter.drawEllipse(QPointF(11, 11), 3.2, 3.2)
        painter.drawEllipse(QPointF(11, 11), 7, 7)
        for index in range(8):
            angle = math.radians(index * 45)
            start = QPointF(11 + math.cos(angle) * 7, 11 + math.sin(angle) * 7)
            end = QPointF(11 + math.cos(angle) * 9, 11 + math.sin(angle) * 9)
            painter.drawLine(start, end)
    elif name == "copy":
        painter.drawRoundedRect(QRectF(7, 7, 11, 12), 1.5, 1.5)
        painter.drawRoundedRect(QRectF(3.5, 3, 11, 12), 1.5, 1.5)
    elif name == "print":
        painter.drawRect(QRectF(6, 2.5, 10, 6))
        painter.drawRoundedRect(QRectF(3, 7.5, 16, 9), 2, 2)
        painter.fillRect(QRectF(6, 13, 10, 6.5), QColor(color))
        painter.setPen(QPen(QColor("#ffffff"), 1.2))
        painter.drawRect(QRectF(7.5, 14.5, 7, 3.5))

    painter.end()
    return QIcon(pixmap)
