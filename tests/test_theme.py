from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication, QComboBox, QMenu

from app.ui.theme import APP_STYLE_SHEET, COLORS, apply_app_theme


def contrast_ratio(first: str, second: str) -> float:
    def luminance(color: str) -> float:
        channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [
            channel / 12.92
            if channel <= 0.04045
            else ((channel + 0.055) / 1.055) ** 2.4
            for channel in channels
        ]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    lighter, darker = sorted((luminance(first), luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


class ThemeTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])
        apply_app_theme(cls.application)

    def assert_palette_is_readable(
        self, palette: QPalette, expected_highlight: str
    ) -> None:
        self.assertEqual(palette.color(QPalette.ColorRole.Base).name(), COLORS.surface)
        self.assertEqual(palette.color(QPalette.ColorRole.Text).name(), COLORS.text)
        self.assertEqual(
            palette.color(QPalette.ColorRole.Highlight).name(), expected_highlight
        )
        self.assertEqual(
            palette.color(QPalette.ColorRole.HighlightedText).name(),
            COLORS.surface if expected_highlight == COLORS.primary else COLORS.text,
        )

    def test_application_uses_canonical_light_palette(self) -> None:
        self.assertEqual(self.application.styleSheet(), APP_STYLE_SHEET)
        self.assert_palette_is_readable(self.application.palette(), COLORS.primary)

    def test_canonical_text_combinations_meet_normal_text_contrast(self) -> None:
        self.assertGreaterEqual(contrast_ratio(COLORS.text, COLORS.surface), 4.5)
        self.assertGreaterEqual(contrast_ratio(COLORS.text, COLORS.primary_soft), 4.5)
        self.assertGreaterEqual(contrast_ratio(COLORS.surface, COLORS.primary), 4.5)

    def test_combo_popup_inherits_readable_palette(self) -> None:
        combo = QComboBox()
        combo.addItems(("Nenhuma", "Segunda-feira", "Terça-feira"))
        combo.show()
        combo.showPopup()
        self.application.processEvents()

        self.assert_palette_is_readable(combo.view().palette(), COLORS.primary_soft)

        combo.hidePopup()
        combo.close()

    def test_menu_inherits_readable_palette(self) -> None:
        menu = QMenu()
        menu.addAction("Editar")
        self.assert_palette_is_readable(menu.palette(), COLORS.primary)


if __name__ == "__main__":
    unittest.main()
