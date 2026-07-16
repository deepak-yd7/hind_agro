from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QAbstractScrollArea,
    QHeaderView,
    QSizePolicy,
)


TABLE_SCROLLBAR_STYLE = """
QScrollBar:horizontal {
    height: 14px;
    background: #E8EFE5;
    border-radius: 7px;
}
QScrollBar::handle:horizontal {
    background: #9DBA9D;
    border-radius: 7px;
    min-width: 30px;
}
QScrollBar:vertical {
    width: 14px;
    background: #E8EFE5;
    border-radius: 7px;
}
QScrollBar::handle:vertical {
    background: #9DBA9D;
    border-radius: 7px;
    min-height: 30px;
}
"""


def _width_map(widths):
    if widths is None:
        return {}
    if isinstance(widths, dict):
        return {int(col): int(width) for col, width in widths.items() if width}
    return {col: int(width) for col, width in enumerate(widths) if width}


def configure_scrollable_table(table, minimum_widths=None):
    """Use real content widths so large values create scrollbars instead of shrinking."""
    widths = _width_map(minimum_widths)
    header = table.horizontalHeader()

    table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    table.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustIgnored)
    table.setWordWrap(False)
    table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    header.setStretchLastSection(False)
    header.setMinimumSectionSize(40)
    for col in range(table.columnCount()):
        header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
        if col in widths:
            table.setColumnWidth(col, widths[col])


def fit_table_columns_to_contents(table, minimum_widths=None, padding=24):
    """Grow columns to fit loaded values, while keeping configured/user widths."""
    widths = _width_map(minimum_widths)
    header = table.horizontalHeader()
    metrics = header.fontMetrics()

    for col in range(table.columnCount()):
        header_item = table.horizontalHeaderItem(col)
        header_width = 0
        if header_item:
            header_width = metrics.horizontalAdvance(header_item.text()) + padding

        content_width = table.sizeHintForColumn(col)
        if content_width < 0:
            content_width = 0

        target = max(
            widths.get(col, 0),
            table.columnWidth(col),
            header_width,
            content_width + padding,
        )
        table.setColumnWidth(col, target)
