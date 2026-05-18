"""Theme manager: light / dark stylesheets and palette colors."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    name: str
    bg: str
    surface: str
    surface_alt: str
    border: str
    text: str
    text_muted: str
    accent: str
    accent_hover: str
    danger: str
    warning: str
    success: str
    info: str

    cell_shift: str
    cell_reduce: str
    cell_accept: str
    cell_goto: str
    cell_first: str
    cell_follow: str
    cell_prod_num: str
    cell_prod_head: str
    cell_prod_body: str
    row_highlight: str

    edit_ok: str
    edit_err: str


LIGHT = Palette(
    name="light",
    bg="#F5F6F8",
    surface="#FFFFFF",
    surface_alt="#FAFAFB",
    border="#E0E3E7",
    text="#1F2933",
    text_muted="#5F6B7A",
    accent="#2E7D32",
    accent_hover="#1B5E20",
    danger="#C62828",
    warning="#EF6C00",
    success="#2E7D32",
    info="#1565C0",
    cell_shift="#D4EDDA",
    cell_reduce="#FFF3CD",
    cell_accept="#CCE5FF",
    cell_goto="#F5F5F5",
    cell_first="#EAF4FB",
    cell_follow="#EAFAF1",
    cell_prod_num="#FFF9C4",
    cell_prod_head="#E8F5E9",
    cell_prod_body="#FAFAFA",
    row_highlight="#D6EAF8",
    edit_ok="#DFF0D8",
    edit_err="#F2DEDE",
)


DARK = Palette(
    name="dark",
    bg="#1A1D21",
    surface="#22262B",
    surface_alt="#2A2E34",
    border="#3A3F46",
    text="#E6E9EF",
    text_muted="#9AA3AE",
    accent="#4CAF50",
    accent_hover="#66BB6A",
    danger="#EF5350",
    warning="#FFA726",
    success="#66BB6A",
    info="#42A5F5",
    cell_shift="#1F4D2A",
    cell_reduce="#5C4A1A",
    cell_accept="#1F3D5C",
    cell_goto="#2A2E34",
    cell_first="#1F3A4D",
    cell_follow="#1F4D3A",
    cell_prod_num="#5C5424",
    cell_prod_head="#1F4D2A",
    cell_prod_body="#2A2E34",
    row_highlight="#1F3D5C",
    edit_ok="#1F4D2A",
    edit_err="#5C2A2A",
)


def stylesheet(p: Palette) -> str:
    return f"""
    QMainWindow, QWidget {{
        background-color: {p.bg};
        color: {p.text};
        font-family: "Segoe UI", "SF Pro Text", Arial, sans-serif;
        font-size: 10pt;
    }}

    QMenuBar {{
        background-color: {p.surface};
        color: {p.text};
        border-bottom: 1px solid {p.border};
        padding: 2px;
    }}
    QMenuBar::item:selected {{
        background-color: {p.surface_alt};
        border-radius: 4px;
    }}
    QMenu {{
        background-color: {p.surface};
        color: {p.text};
        border: 1px solid {p.border};
        padding: 4px;
    }}
    QMenu::item:selected {{
        background-color: {p.accent};
        color: white;
        border-radius: 3px;
    }}

    QStatusBar {{
        background-color: {p.surface};
        color: {p.text_muted};
        border-top: 1px solid {p.border};
    }}

    QPushButton {{
        background-color: {p.surface};
        color: {p.text};
        border: 1px solid {p.border};
        border-radius: 6px;
        padding: 6px 14px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: {p.surface_alt};
        border-color: {p.accent};
    }}
    QPushButton:pressed {{
        background-color: {p.border};
    }}
    QPushButton:disabled {{
        color: {p.text_muted};
        background-color: {p.surface_alt};
    }}

    QPushButton#analyzeBtn {{
        background-color: {p.accent};
        color: white;
        border: none;
        font-weight: bold;
    }}
    QPushButton#analyzeBtn:hover {{
        background-color: {p.accent_hover};
    }}
    QPushButton#analyzeBtn:disabled {{
        background-color: {p.text_muted};
    }}

    QPushButton#themeBtn {{
        padding: 6px 12px;
        min-width: 80px;
    }}

    QGroupBox {{
        background-color: {p.surface};
        border: 1px solid {p.border};
        border-radius: 8px;
        margin-top: 14px;
        padding-top: 8px;
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
        color: {p.text_muted};
    }}

    QTabWidget::pane {{
        background-color: {p.surface};
        border: 1px solid {p.border};
        border-radius: 6px;
        top: -1px;
    }}
    QTabBar::tab {{
        background-color: {p.surface_alt};
        color: {p.text_muted};
        padding: 8px 16px;
        border: 1px solid {p.border};
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        margin-right: 2px;
    }}
    QTabBar::tab:selected {{
        background-color: {p.surface};
        color: {p.text};
        border-bottom: 2px solid {p.accent};
    }}
    QTabBar::tab:hover {{
        color: {p.text};
    }}

    QTextEdit, QPlainTextEdit {{
        background-color: {p.surface};
        color: {p.text};
        border: 1px solid {p.border};
        border-radius: 6px;
        padding: 8px;
        selection-background-color: {p.accent};
        selection-color: white;
    }}

    QListWidget {{
        background-color: {p.surface};
        color: {p.text};
        border: 1px solid {p.border};
        border-radius: 6px;
        padding: 4px;
        outline: none;
    }}
    QListWidget::item {{
        padding: 8px 10px;
        border-radius: 4px;
        margin: 2px 0;
    }}
    QListWidget::item:hover {{
        background-color: {p.surface_alt};
    }}
    QListWidget::item:selected {{
        background-color: {p.accent};
        color: white;
    }}

    QTableWidget {{
        background-color: {p.surface};
        color: {p.text};
        border: 1px solid {p.border};
        border-radius: 6px;
        gridline-color: {p.border};
        selection-background-color: {p.accent};
        selection-color: white;
    }}
    QHeaderView::section {{
        background-color: {p.surface_alt};
        color: {p.text};
        padding: 6px 10px;
        border: none;
        border-right: 1px solid {p.border};
        border-bottom: 1px solid {p.border};
        font-weight: 600;
    }}
    QTableCornerButton::section {{
        background-color: {p.surface_alt};
        border: 1px solid {p.border};
    }}

    QScrollBar:vertical {{
        background-color: {p.bg};
        width: 12px;
        border: none;
    }}
    QScrollBar::handle:vertical {{
        background-color: {p.border};
        border-radius: 6px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {p.text_muted};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}

    QScrollBar:horizontal {{
        background-color: {p.bg};
        height: 12px;
        border: none;
    }}
    QScrollBar::handle:horizontal {{
        background-color: {p.border};
        border-radius: 6px;
        min-width: 30px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background-color: {p.text_muted};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
    }}

    QSplitter::handle {{
        background-color: {p.border};
    }}
    QSplitter::handle:horizontal {{
        width: 3px;
    }}
    QSplitter::handle:vertical {{
        height: 3px;
    }}

    QToolTip {{
        background-color: {p.surface_alt};
        color: {p.text};
        border: 1px solid {p.border};
        border-radius: 4px;
        padding: 4px 8px;
    }}

    QLabel#sectionTitle {{
        color: {p.text_muted};
        font-weight: 600;
        font-size: 9pt;
        padding: 4px 0;
    }}

    QLabel#fileLabel {{
        color: {p.text};
        padding: 4px 8px;
    }}
    """
