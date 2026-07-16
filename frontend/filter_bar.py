"""
frontend/filter_bar.py
======================
Reusable filter bar widget used by every page.
Features:
  - Search box (searches across all visible columns)
  - Column selector (choose which column to search in)
  - Dropdown filter (for status/role/category columns)
  - Refresh button (manual)
  - Auto-refresh every 5 seconds (toggle checkbox)
  - Live record count label
"""
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QCheckBox, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor

FILTER_STYLE = """
QFrame#filter_frame {
    background: white;
    border-radius: 10px;
    border: 1px solid #D8ECD0;
}
QLineEdit#search_box {
    border: 1.5px solid #C8DFC0;
    border-radius: 7px;
    padding: 7px 13px;
    font-size: 13px;
    background: #F7FAF5;
    color: #1A3A1A;
    min-width: 200px;
}
QLineEdit#search_box:focus {
    border: 1.5px solid #2D7A2D;
    background: white;
}
QComboBox#col_combo, QComboBox#drop_combo {
    border: 1.5px solid #C8DFC0;
    border-radius: 7px;
    padding: 7px 10px;
    font-size: 12px;
    background: white;
    color: #1A3A1A;
    min-width: 110px;
}
QComboBox#col_combo:focus, QComboBox#drop_combo:focus {
    border: 1.5px solid #2D7A2D;
}
QPushButton#refresh_btn {
    background: #2D4A2D;
    color: white;
    border: none;
    border-radius: 7px;
    padding: 7px 18px;
    font-size: 13px;
    font-weight: bold;
}
QPushButton#refresh_btn:hover  { background: #3D6B3D; }
QPushButton#refresh_btn:pressed{ background: #1E3A1E; }
QPushButton#clear_btn {
    background: #E8EDE8;
    color: #2D4A2D;
    border: none;
    border-radius: 7px;
    padding: 7px 14px;
    font-size: 13px;
}
QPushButton#clear_btn:hover { background: #D0DAD0; }
QCheckBox#auto_check {
    font-size: 12px;
    color: #4A7A4A;
    spacing: 6px;
}
QCheckBox#auto_check::indicator {
    width: 16px; height: 16px;
    border: 2px solid #4A7C4A;
    border-radius: 4px;
}
QCheckBox#auto_check::indicator:checked {
    background: #2D7A2D;
    border: 2px solid #2D7A2D;
}
QLabel#count_lbl {
    font-size: 11px;
    color: #7A9A7A;
    font-style: italic;
}
QLabel#timer_lbl {
    font-size: 11px;
    color: #4A9A4A;
    font-weight: bold;
}

QComboBox#col_combo QAbstractItemView,
QComboBox#drop_combo QAbstractItemView {
    background: white;
    color: #111111;
    selection-background-color: #D6EDD6;
    selection-color: #111111;
    outline: 0;
}
"""


class FilterBar(QFrame):
    """
    Emits:
      filter_changed(search_text, column_index, dropdown_value)
      refresh_requested()
    """
    filter_changed   = pyqtSignal(str, int, str)
    refresh_requested = pyqtSignal()

    def __init__(self,
                 columns: list,           # list of column names for the column selector
                 dropdown_label: str = "", # label for optional dropdown filter
                 dropdown_items: list = None, # items in the dropdown
                 auto_refresh_sec: int = 5,
                 parent=None):
        super().__init__(parent)
        self.setObjectName("filter_frame")
        self.setStyleSheet(FILTER_STYLE)

        self._auto_sec = auto_refresh_sec
        self._countdown = auto_refresh_sec

        main = QVBoxLayout(self)
        main.setContentsMargins(14, 10, 14, 10)
        main.setSpacing(8)

        # ── Row 1: Search + column + dropdown + buttons ────────────────────────
        row1 = QHBoxLayout()
        row1.setSpacing(10)

        # Search box
        self.search_box = QLineEdit()
        self.search_box.setObjectName("search_box")
        self.search_box.setPlaceholderText("🔍  Search…")
        self.search_box.setFixedHeight(36)
        self.search_box.textChanged.connect(self._emit_filter)
        row1.addWidget(self.search_box)

        # Column selector
        col_lbl = QLabel("in:")
        col_lbl.setStyleSheet("font-size:12px;color:#7A9A7A;")
        self.col_combo = QComboBox()
        self.col_combo.setObjectName("col_combo")
        self.col_combo.setFixedHeight(36)
        self.col_combo.addItem("All Columns")
        for c in columns:
            self.col_combo.addItem(c)
        self.col_combo.currentIndexChanged.connect(self._emit_filter)
        row1.addWidget(col_lbl)
        row1.addWidget(self.col_combo)

        # Optional dropdown filter
        self.drop_combo = None
        if dropdown_label and dropdown_items:
            drop_lbl = QLabel(f"{dropdown_label}:")
            drop_lbl.setStyleSheet("font-size:12px;color:black;")
            self.drop_combo = QComboBox()
            self.drop_combo.setObjectName("drop_combo")
            self.drop_combo.setFixedHeight(36)
            self.drop_combo.addItem(f"All {dropdown_label}s")
            for item in dropdown_items:
                self.drop_combo.addItem(item)
            self.drop_combo.currentIndexChanged.connect(self._emit_filter)
            row1.addWidget(drop_lbl)
            row1.addWidget(self.drop_combo)

        row1.addStretch()

        # Clear button
        self.clear_btn = QPushButton("✕ Clear")
        self.clear_btn.setObjectName("clear_btn")
        self.clear_btn.setFixedHeight(36)
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.clicked.connect(self.clear_filters)
        row1.addWidget(self.clear_btn)

        # Refresh button
        self.refresh_btn = QPushButton("↻  Refresh")
        self.refresh_btn.setObjectName("refresh_btn")
        self.refresh_btn.setFixedHeight(36)
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self._manual_refresh)
        row1.addWidget(self.refresh_btn)

        main.addLayout(row1)

        # ── Row 2: auto-refresh toggle + count label ───────────────────────────
        row2 = QHBoxLayout()
        row2.setSpacing(14)

        self.auto_check = QCheckBox("Auto-refresh fallback (5s)")
        self.auto_check.setObjectName("auto_check")
        self.auto_check.setChecked(True)
        self.auto_check.stateChanged.connect(self._toggle_auto)
        row2.addWidget(self.auto_check)

        self.timer_lbl = QLabel("↻ 5s")
        self.timer_lbl.setObjectName("timer_lbl")
        row2.addWidget(self.timer_lbl)

        row2.addStretch()

        self.count_lbl = QLabel("Loading…")
        self.count_lbl.setObjectName("count_lbl")
        row2.addWidget(self.count_lbl)

        main.addLayout(row2)

        # ── Auto-refresh timer ─────────────────────────────────────────────────
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._auto_refresh)
        self._refresh_timer.start(self._auto_sec * 1000)

        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start(1000)

    # ── Public API ─────────────────────────────────────────────────────────────

    def set_count(self, shown: int, total: int):
        if shown == total:
            self.count_lbl.setText(f"{total} record{'s' if total != 1 else ''}")
        else:
            self.count_lbl.setText(f"Showing {shown} of {total} records")

    def clear_filters(self):
        self.search_box.blockSignals(True)
        self.search_box.clear()
        self.search_box.blockSignals(False)
        self.col_combo.setCurrentIndex(0)
        if self.drop_combo:
            self.drop_combo.setCurrentIndex(0)
        self._emit_filter()

    def get_search(self) -> str:
        return self.search_box.text().strip()

    def get_column(self) -> int:
        """Returns 0 for All Columns, else 1-based column index."""
        return self.col_combo.currentIndex()

    def get_dropdown(self) -> str:
        if self.drop_combo:
            idx = self.drop_combo.currentIndex()
            return "" if idx == 0 else self.drop_combo.currentText()
        return ""

    # ── Internals ──────────────────────────────────────────────────────────────

    def _emit_filter(self):
        self.filter_changed.emit(
            self.get_search(),
            self.get_column(),
            self.get_dropdown(),
        )

    def _manual_refresh(self):
        self._countdown = self._auto_sec
        self.refresh_requested.emit()

    def _auto_refresh(self):
        if self.auto_check.isChecked():
            self.refresh_requested.emit()

    def _tick(self):
        if self.auto_check.isChecked():
            self._countdown -= 1
            if self._countdown <= 0:
                self._countdown = self._auto_sec
            self.timer_lbl.setText(f"↻ {self._countdown}s")
            self.timer_lbl.setVisible(True)
        else:
            self.timer_lbl.setVisible(False)

    def _toggle_auto(self, state):
        if state:
            self._refresh_timer.start(self._auto_sec * 1000)
            self._tick_timer.start(1000)
            self._countdown = self._auto_sec
        else:
            self._refresh_timer.stop()
            self._tick_timer.stop()
            self.timer_lbl.setVisible(False)
