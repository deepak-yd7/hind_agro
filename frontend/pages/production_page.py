"""
frontend/pages/production_page.py
===================================
Production tracking with Lot Numbers.

Flow: 1st Entry → Germination → Transplanting → Hardening (Stays here for processing) → Scrap

5 tabs:
  All Lots | Germination | Transplanting | Hardening (→ Inventory) | Scrap
"""

from backend.realtime import db_signals
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QDialog, QFormLayout, QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox,
    QComboBox, QMessageBox, QHeaderView, QSizePolicy, QTabWidget,
    QFrame, QDateTimeEdit, QScrollArea, QProgressBar
)
from PyQt6.QtCore import Qt, QSize, QDateTime
from PyQt6.QtGui import QColor, QFont
from backend.database import get_table_columns
from frontend.filter_bar import FilterBar
from frontend.table_utils import (
    TABLE_SCROLLBAR_STYLE,
    configure_scrollable_table,
    fit_table_columns_to_contents,
)
from models.user_model import (
    STAGE_GERMINATION, STAGE_TRANSPLANTING, STAGE_HARDENING,
    STAGE_SALE, STAGE_SCRAP, STAGE_ORDER, STAGE_COLORS
)

# ── Shared styles ──────────────────────────────────────────────────────────────
TABLE_STYLE = """
QWidget { font-family: 'Segoe UI', Arial, sans-serif; }
QTabWidget::pane  { border: none; background: #F5F7F2; }
QTabBar::tab {
    background: #E8EDE8; color: #2D4A2D; border: none;
    border-radius: 8px 8px 0 0; padding: 10px 20px;
    font-size: 13px; font-weight: bold; margin-right: 4px;
}
QTabBar::tab:selected { background: #2D4A2D; color: white; }
QTabBar::tab:hover    { background: #C8DFC0; }
QTableWidget {
    background: white; border-radius: 10px; border: 1px solid #D8E8D0;
    gridline-color: #EEF5EA; font-size: 13px; outline: none;
}
QTableWidget::item { padding: 0 12px; color: #1A3A1A; border: none; }
QTableWidget::item:selected { background: #D6EDD6; color: #1A3A1A; }
QTableWidget::item:hover    { background: #EEF8EE; }
QHeaderView::section {
    background: #EAF3E4; color: #2D5A2D; font-weight: bold; font-size: 12px;
    border: none; border-bottom: 2px solid #C8DFC0; padding: 10px 12px;
}
"""

DIALOG_STYLE = """
QDialog { background: #F7FAF5; }
QLabel  { font-size: 13px; color: #2D4A2D; font-weight: 500; }
QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateTimeEdit {
    border: 1.5px solid #C8DFC0; border-radius: 6px;
    padding: 7px 11px; font-size: 13px; background: white; color: #1A3A1A;
}
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QComboBox:focus, QDateTimeEdit:focus { border: 1.5px solid #4A7C4A; }
QComboBox QAbstractItemView {
    background: white;
    color: #111111;
    selection-background-color: #D6EDD6;
    selection-color: #111111;
}
"""

SCRAP_REASONS = [
    "Disease / Pest attack",
    "Poor germination",
    "Physical damage",
    "Weather damage",
    "Root rot",
    "Wilting / Drying",
    "Quality rejection",
    "Other",
]


STAGE_FIELDS = {
    "GERMINATION": ["plant_name", "category", "seed_qty", "location"],
    "TRANSPLANTING": ["tray_type", "tray_count", "location"],
    "HARDENING": ["price_per_plant", "location"],
    "SCRAP": ["scrap_qty", "scrap_reason", "location", "done_by"]
}


# --- CHANGED HERE: Removed STAGE_HARDENING: STAGE_SALE to keep data in Hardening ---
NEXT_STAGE = {
    STAGE_GERMINATION: STAGE_TRANSPLANTING,
    STAGE_TRANSPLANTING: STAGE_HARDENING,
}
# -----------------------------------------------------------------------------------


# ── Helpers ────────────────────────────────────────────────────────────────────
def _act_btn(text, bg, hover, w=90, h=32):
    b = QPushButton(text)
    b.setFixedSize(QSize(w, h))
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setStyleSheet(
        f"QPushButton{{background:{bg};color:white;font-size:12px;"
        f"font-weight:bold;border:none;border-radius:6px;}}"
        f"QPushButton:hover{{background:{hover};}}"
    )
    return b


def _stage_badge(stage: str) -> QLabel:
    color = STAGE_COLORS.get(stage, "#888")
    lbl = QLabel(f"  {stage}  ")
    lbl.setStyleSheet(
        f"background:{color};color:white;border-radius:8px;"
        f"font-size:11px;font-weight:bold;padding:3px 8px;"
    )
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return lbl


def _ci(text, center=True, bold=False, color=None):
    it = QTableWidgetItem(str(text))
    if center:
        it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    if bold:
        f = it.font(); f.setBold(True); it.setFont(f)
    if color:
        it.setForeground(QColor(color))
    return it


# ─────────────────────────────────────────────────────────────────────────────
#  Dialogs
# ─────────────────────────────────────────────────────────────────────────────

class NewLotDialog(QDialog):
    """First Entry — create a new production lot (Germination stage)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Production Lot — Germination")
        self.setMinimumWidth(500)
        self.setStyleSheet(DIALOG_STYLE)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(14)

        # Title
        title = QLabel("🌱  New Production Lot")
        title.setStyleSheet("font-size:18px;font-weight:bold;color:#1E3A1E;")
        lay.addWidget(title)

        # Auto lot number
        from services.user_service import ProductionService
        lot_num = ProductionService.next_lot_number()
        lot_info = QLabel(f"Lot Number:  {lot_num}")
        lot_info.setStyleSheet(
            "background:#EAF3E4;border-radius:8px;padding:10px 14px;"
            "font-size:14px;font-weight:bold;color:#1E3A1E;"
        )
        lay.addWidget(lot_info)
        self._lot_number = lot_num

        # Form
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # 🌱 Germination fields
        self.plant_edit = QLineEdit()
        self.plant_edit.setPlaceholderText("e.g. Tomato, Rose, Marigold")
        self.plant_edit.setFixedHeight(38)

        self.variety_edit = QLineEdit()
        self.variety_edit.setPlaceholderText("e.g. Indoor, Flowering, Hybrid F1")
        self.variety_edit.setFixedHeight(38)

        self.seed_qty_spin = QSpinBox()
        self.seed_qty_spin.setMinimum(1)
        self.seed_qty_spin.setMaximum(999999)
        self.seed_qty_spin.setValue(0)
        self.seed_qty_spin.setFixedHeight(38)
        self.seed_qty_spin.setSuffix(" grams")

        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("e.g. Greenhouse A, Bed 1")
        self.location_edit.setFixedHeight(38)

        # Common fields
        self.by_edit = QLineEdit()
        self.by_edit.setPlaceholderText("Who is creating this lot?")
        self.by_edit.setFixedHeight(38)

        self.notes_edit = QTextEdit()
        self.notes_edit.setFixedHeight(60)
        self.notes_edit.setPlaceholderText("Seed batch, source, etc.")

        # Add rows
        form.addRow("Plant Name *", self.plant_edit)
        form.addRow("Category", self.variety_edit)
        form.addRow("Seed Quantity (grams)", self.seed_qty_spin)
        form.addRow("Location", self.location_edit)
        form.addRow("Created By", self.by_edit)
        form.addRow("Notes", self.notes_edit)
        lay.addLayout(form)

        # Buttons
        btns = QHBoxLayout(); btns.setSpacing(10)
        c_btn = QPushButton("Cancel"); c_btn.setFixedHeight(40)
        c_btn.setStyleSheet("QPushButton{background:#E8EDE8;color:#2D4A2D;border:none;"
                            "border-radius:8px;padding:0 22px;}")
        s_btn = QPushButton("🌱  Create Lot"); s_btn.setFixedHeight(40)
        s_btn.setStyleSheet("QPushButton{background:#1E5C1E;color:white;border:none;"
                            "border-radius:8px;padding:0 26px;font-weight:bold;}"
                            "QPushButton:hover{background:#2E7D2E;}")
        c_btn.clicked.connect(self.reject)
        s_btn.clicked.connect(self.accept)
        btns.addStretch(); btns.addWidget(c_btn); btns.addWidget(s_btn)
        lay.addLayout(btns)


class AdvanceStageDialog(QDialog):
    """Move lot to the next stage."""
    def __init__(self, lot, next_stage: str, parent=None):
        super().__init__(parent)
        self.lot = lot
        self.next_stage = next_stage
        stage_color = STAGE_COLORS.get(next_stage, "#2D4A2D")
        self.setWindowTitle(f"Advance to {next_stage} — {lot.lot_number}")
        self.setMinimumWidth(500)
        self.setStyleSheet(DIALOG_STYLE)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(14)

        # Header
        title = QLabel(f"Move to  →  {next_stage}")
        title.setStyleSheet(f"font-size:18px;font-weight:bold;color:{stage_color};")
        lay.addWidget(title)

        lot_info = QLabel(
            f"Lot: {lot.lot_number}   |   Plant: {lot.plant_name}"
            + (f"   |   Category: {lot.variety}" if lot.variety else "")
            + f"\nCurrent Stage: {lot.current_stage}"
            + f"   |   Current Qty: {lot.current_quantity}"
        )
        lot_info.setStyleSheet("background:#EAF3E4;border-radius:8px;padding:10px 14px;"
                               "font-size:13px;color:#1A3A1A;")
        lot_info.setWordWrap(True)
        lay.addWidget(lot_info)

        # Stage-specific note
        if next_stage == STAGE_HARDENING:
            note = QLabel("Reaching Hardening means this lot is ready for further processing.")
            note.setStyleSheet("background:#FFF8E1;border-radius:6px;padding:8px 12px;"
                               "font-size:12px;color:#7D6608;font-weight:bold;")
            note.setWordWrap(True)
            lay.addWidget(note)

        # Form
        form = QFormLayout(); form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # 🌱 Germination → only seed qty + location
        if next_stage == STAGE_GERMINATION:
            self.seed_qty_spin = QSpinBox()
            self.seed_qty_spin.setMinimum(1); self.seed_qty_spin.setMaximum(999999)
            self.seed_qty_spin.setSuffix(" grams")
            self.seed_qty_spin.setFixedHeight(38)

            self.location_edit = QLineEdit()
            self.location_edit.setPlaceholderText("e.g. Greenhouse A")
            self.location_edit.setFixedHeight(38)

            form.addRow("Seed Quantity (grams)", self.seed_qty_spin)
            form.addRow("Location", self.location_edit)

        # 🌱 Transplanting → tray type + tray count + location
        elif next_stage == STAGE_TRANSPLANTING:
            self.tray_type_combo = QComboBox()
            self.tray_type_combo.addItems(["104-cell", "198-cell", "160-cell", "67-cell", "other"])
            self.tray_type_combo.setEditable(True)
            self.tray_type_combo.setFixedHeight(38)

            self.tray_spin = QSpinBox()
            self.tray_spin.setMinimum(1); self.tray_spin.setMaximum(9999)
            self.tray_spin.setSuffix(" trays")
            self.tray_spin.setFixedHeight(38)

            self.location_edit = QLineEdit()
            self.location_edit.setPlaceholderText("e.g. Greenhouse B")
            self.location_edit.setFixedHeight(38)

            form.addRow("Tray Type", self.tray_type_combo)
            form.addRow("No. of Trays", self.tray_spin)
            form.addRow("Location", self.location_edit)

        # 🌱 Hardening → price per plant + location
        elif next_stage == STAGE_HARDENING:
            self.price_spin = QDoubleSpinBox()
            self.price_spin.setMinimum(0); self.price_spin.setMaximum(999999)
            self.price_spin.setDecimals(2)
            self.price_spin.setPrefix("Rs ")
            self.price_spin.setFixedHeight(38)

            self.location_edit = QLineEdit()
            self.location_edit.setPlaceholderText("e.g. Greenhouse C")
            self.location_edit.setFixedHeight(38)

            form.addRow("Price per Plant", self.price_spin)
            form.addRow("Location", self.location_edit)

        # Common fields for all stages
        self.done_by_edit = QLineEdit()
        self.done_by_edit.setPlaceholderText("Staff name")
        self.done_by_edit.setFixedHeight(38)

        self.date_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setFixedHeight(38)
        self.date_edit.setDisplayFormat("dd MMM yyyy  hh:mm")

        self.notes_edit = QTextEdit(); self.notes_edit.setFixedHeight(60)

        form.addRow("Done By", self.done_by_edit)
        form.addRow("Date", self.date_edit)
        form.addRow("Notes", self.notes_edit)
        lay.addLayout(form)

        # Buttons
        btns = QHBoxLayout(); btns.setSpacing(10)
        c_btn = QPushButton("Cancel"); c_btn.setFixedHeight(40)
        c_btn.setStyleSheet("QPushButton{background:#E8EDE8;color:#2D4A2D;border:none;"
                            "border-radius:8px;padding:0 22px;}")
        s_btn = QPushButton(f"→  Move to {next_stage}"); s_btn.setFixedHeight(40)
        s_btn.setStyleSheet(
            f"QPushButton{{background:{stage_color};color:white;border:none;"
            f"border-radius:8px;padding:0 24px;font-weight:bold;}}"
            f"QPushButton:hover{{opacity:0.9;}}"
        )
        c_btn.clicked.connect(self.reject)
        s_btn.clicked.connect(self.accept)
        btns.addStretch(); btns.addWidget(c_btn); btns.addWidget(s_btn)
        lay.addLayout(btns)


class ScrapDialog(QDialog):
    """Record scrap at any stage."""
    def __init__(self, lot, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Record Scrap — {lot.lot_number}")
        self.setFixedWidth(460)
        self.setStyleSheet(DIALOG_STYLE)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(14)

        title = QLabel("❌  Record Scrap")
        title.setStyleSheet("font-size:18px;font-weight:bold;color:#C0392B;")
        lay.addWidget(title)

        info = QLabel(f"Lot: {lot.lot_number}  —  {lot.plant_name}\n"
                      f"Current Stage: {lot.current_stage}  |  Qty: {lot.current_quantity}")
        info.setStyleSheet("background:#FDECEA;border-radius:8px;padding:10px;"
                           "font-size:13px;color:#1A3A1A;")
        lay.addWidget(info)

        form = QFormLayout(); form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.qty_spin = QSpinBox()
        self.qty_spin.setMinimum(1); self.qty_spin.setMaximum(lot.current_quantity or 999999)
        self.qty_spin.setFixedHeight(38); self.qty_spin.setSuffix("  plants")

        self.reason_combo = QComboBox(); self.reason_combo.setFixedHeight(38)
        self.reason_combo.addItems(SCRAP_REASONS)

        self.by_edit = QLineEdit(); self.by_edit.setFixedHeight(38)
        self.by_edit.setPlaceholderText("Who recorded this?")

        self.notes_edit = QTextEdit(); self.notes_edit.setFixedHeight(60)

        form.addRow("Quantity Scrapped", self.qty_spin)
        form.addRow("Reason",            self.reason_combo)
        form.addRow("Recorded By",       self.by_edit)
        form.addRow("Notes",             self.notes_edit)
        lay.addLayout(form)

        btns = QHBoxLayout(); btns.setSpacing(10)
        c_btn = QPushButton("Cancel"); c_btn.setFixedHeight(40)
        c_btn.setStyleSheet("QPushButton{background:#E8EDE8;color:#2D4A2D;border:none;"
                            "border-radius:8px;padding:0 22px;}")
        s_btn = QPushButton("Record Scrap"); s_btn.setFixedHeight(40)
        s_btn.setStyleSheet("QPushButton{background:#C0392B;color:white;border:none;"
                            "border-radius:8px;padding:0 24px;font-weight:bold;}"
                            "QPushButton:hover{background:#E74C3C;}")
        c_btn.clicked.connect(self.reject)
        s_btn.clicked.connect(self.accept)
        btns.addStretch(); btns.addWidget(c_btn); btns.addWidget(s_btn)
        lay.addLayout(btns)


class LotDetailDialog(QDialog):
    """Full history / timeline of a lot."""
    def __init__(self, lot_id: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Lot Detail")
        self.setMinimumSize(700, 500)
        self.setStyleSheet(DIALOG_STYLE)

        from services.user_service import ProductionService
        lot = ProductionService.get_lot_with_stages(lot_id)
        if not lot:
            self.reject(); return

        self.setWindowTitle(f"Lot Detail — {lot.lot_number}")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        # Header
        hdr = QHBoxLayout()
        title = QLabel(f"📋  {lot.lot_number}")
        title.setStyleSheet("font-size:20px;font-weight:bold;color:#1E3A1E;")
        plant = QLabel(f"{lot.plant_name}" + (f"  |  Category: {lot.variety}" if lot.variety else ""))
        plant.setStyleSheet("font-size:14px;color:#4A7A4A;")
        hdr.addWidget(title); hdr.addSpacing(16); hdr.addWidget(plant); hdr.addStretch()
        # current stage badge
        badge = _stage_badge(lot.current_stage)
        hdr.addWidget(badge)
        lay.addLayout(hdr)

        # Summary bar
        summary = QLabel(
            f"Initial Qty: {lot.quantity}   |   "
            f"Current Qty: {lot.current_quantity}   |   "
            f"Total Scrapped: {lot.total_scrapped}   |   "
            f"Trays: {lot.tray_count}   |   "
            f"Created: {str(lot.created_at)[:10] if lot.created_at else '—'}"
        )
        summary.setStyleSheet("background:#EAF3E4;border-radius:8px;padding:10px 14px;"
                              "font-size:12px;color:#1A3A1A;")
        lay.addWidget(summary)

        # Timeline
        tl_lbl = QLabel("📅  Stage History")
        tl_lbl.setStyleSheet("font-size:13px;font-weight:bold;color:#1E3A1E;")
        lay.addWidget(tl_lbl)

        tbl = QTableWidget()
        tbl.setColumnCount(8)
        tbl.setHorizontalHeaderLabels([
            "Stage","Date","Qty In","Qty Out","Scrap","Trays","Location","Done By"
        ])
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl.verticalHeader().setVisible(False)
        tbl.setAlternatingRowColors(True)
        tbl.setStyleSheet(TABLE_STYLE + "QTableWidget{alternate-background-color:#F5FAF3;}" + TABLE_SCROLLBAR_STYLE)
        stage_column_widths = [120, 130, 80, 80, 70, 70, 180, 180]
        configure_scrollable_table(tbl, stage_column_widths)

        tbl.setRowCount(len(lot.stages))
        for row, s in enumerate(lot.stages):
            tbl.setRowHeight(row, 44)
            color = STAGE_COLORS.get(s.stage, "#555")
            si = QTableWidgetItem(s.stage)
            si.setForeground(QColor(color))
            f = si.font(); f.setBold(True); si.setFont(f)
            si.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            tbl.setItem(row, 0, si)
            date_value = s.stage_date if s.stage_date else s.created_at
            date_str = str(date_value)[:16] if date_value else "—"
            tbl.setItem(row, 1, _ci(date_str))
            tbl.setItem(row, 2, _ci(str(s.quantity_in)))
            tbl.setItem(row, 3, _ci(str(s.quantity_out), bold=True))
            scrap_item = _ci(str(s.quantity_scrap))
            if s.quantity_scrap > 0: scrap_item.setForeground(QColor("#C0392B"))
            tbl.setItem(row, 4, scrap_item)
            tbl.setItem(row, 5, _ci(str(s.tray_count)))
            tbl.setItem(row, 6, QTableWidgetItem(s.location or ""))
            tbl.setItem(row, 7, QTableWidgetItem(s.done_by or ""))
        fit_table_columns_to_contents(tbl, stage_column_widths)

        lay.addWidget(tbl)

        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(38)
        close_btn.setStyleSheet("QPushButton{background:#2D4A2D;color:white;border:none;"
                                "border-radius:8px;padding:0 28px;font-weight:bold;}"
                                "QPushButton:hover{background:#3D6B3D;}")
        close_btn.clicked.connect(self.accept)
        lay.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)


# ─────────────────────────────────────────────────────────────────────────────
#  Lot Table (reusable for each tab)
# ─────────────────────────────────────────────────────────────────────────────

class LotTableWidget(QWidget):
    """
    Shows a filtered list of lots for one stage.
    stage_filter = "" means show all lots.
    """

    def __init__(self, stage_filter: str = "", show_actions: bool = True):
        super().__init__()
        self.stage_filter = stage_filter
        self.show_actions = show_actions

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 8, 0, 0)
        lay.setSpacing(10)

        # Filter bar
        self.filter_bar = FilterBar(
            columns=["Lot No.", "Plant Name", "Category", "Created By"],
            auto_refresh_sec=5,
        )
        self.filter_bar.filter_changed.connect(lambda s, c, d: self.load())
        self.filter_bar.refresh_requested.connect(self.load)
        lay.addWidget(self.filter_bar)

        # Table
        self.table = QTableWidget()

        # 1. Define ALL base columns unconditionally (including Price / Plant)
        cols = ["Lot No.", "Plant Name", "Category", "Stage", "Init Qty",
                "Curr Qty", "Trays", "Tray Type", "Seed Qty", "Location",
                "Price / Plant", "Scrapped", "Created"]

        if show_actions:
            cols.append("Actions")

        # 2. Apply the uniform column widths (includes the 90px width for Price)
        self._column_min_widths = [100, 180, 140, 110, 75, 75, 60, 90, 75, 120, 90, 70, 90, 300]

        # 3. Apply the total count and headers to the table
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)

        # 4. Apply widths
        self._column_min_widths = self._column_min_widths[:len(cols)]
        configure_scrollable_table(self.table, self._column_min_widths)

        # Table Styling & Behaviors
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(
            TABLE_STYLE + "QTableWidget{alternate-background-color:#F5FAF3;}" + TABLE_SCROLLBAR_STYLE
        )
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        lay.addWidget(self.table)

        self.load()

    def load(self):
        try:
            from services.user_service import ProductionService
            q = self.filter_bar.get_search().lower()
            col = self.filter_bar.get_column()

            all_lots = ProductionService.get_all_lots(self.stage_filter)

            if q:
                def match(lot):
                    fields = [lot.lot_number, lot.plant_name,
                              lot.variety or "", lot.created_by or ""]
                    if col == 0:
                        return any(q in f.lower() for f in fields)
                    elif col <= len(fields):
                        return q in fields[col - 1].lower()
                    return True

                lots = [l for l in all_lots if match(l)]
            else:
                lots = all_lots

            self.filter_bar.set_count(len(lots), len(all_lots))

            # Fetch stages for each lot
            from services.user_service import ProductionService as PS
            lots_full = [PS.get_lot_with_stages(l.id) for l in lots]

            self.table.setRowCount(0)
            self.table.setRowCount(len(lots_full))

            # Dynamically grab the last column index for the action buttons
            action_col = self.table.columnCount() - 1 if self.show_actions else -1

            for row, lot in enumerate(lots_full):
                if not lot:
                    continue
                self.table.setRowHeight(row, 56)

                # Lot number
                ln = QTableWidgetItem(lot.lot_number)
                ln.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
                ln.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 0, ln)

                # Plant name
                self.table.setItem(row, 1, QTableWidgetItem(lot.plant_name))
                self.table.setItem(row, 2, QTableWidgetItem(lot.variety or ""))

                # Stage badge (colored text)
                stage_item = _ci(lot.current_stage, bold=True,
                                 color=STAGE_COLORS.get(lot.current_stage, "#555"))
                self.table.setItem(row, 3, stage_item)

                self.table.setItem(row, 4, _ci(str(lot.quantity)))
                curr_item = _ci(str(lot.current_quantity), bold=True)
                self.table.setItem(row, 5, curr_item)
                self.table.setItem(row, 6, _ci(str(lot.tray_count)))

                # New fields: Tray Type, Seed Quantity, Location
                self.table.setItem(row, 7, _ci(lot.tray_type or "-"))
                self.table.setItem(row, 8, _ci(str(lot.seed_quantity) if lot.seed_quantity > 0 else "-"))
                self.table.setItem(row, 9, QTableWidgetItem(lot.location or ""))

                # --- CORRECTED PRICE EXTRACTION ---
                col_idx = 10

                # The price is stored in the stages, not the lot itself.
                # We loop through the stages to find if a price was set (usually in Hardening).
                price = 0.0
                if lot.stages:
                    for s in lot.stages:
                        if s.price and s.price > 0:
                            price = s.price

                self.table.setItem(row, col_idx, _ci(f"Rs {price:.2f}"))
                col_idx += 1
                # ----------------------------------

                scrap_item = _ci(str(lot.total_scrapped))
                if lot.total_scrapped > 0:
                    scrap_item.setForeground(QColor("#C0392B"))
                self.table.setItem(row, col_idx, scrap_item)
                col_idx += 1

                date_str = str(lot.created_at)[:10] if lot.created_at else "—"
                self.table.setItem(row, col_idx, _ci(date_str))
                col_idx += 1

                if self.show_actions:
                    bw = QWidget()
                    bw.setStyleSheet("background:transparent;")

                    bl = QHBoxLayout(bw)
                    bl.setContentsMargins(6, 5, 6, 5)
                    bl.setSpacing(5)
                    bl.setAlignment(
                        Qt.AlignmentFlag.AlignVCenter |
                        Qt.AlignmentFlag.AlignLeft
                    )

                    # Detail
                    view_btn = _act_btn("Detail", "#1A5276", "#2471A3", w=65)
                    view_btn.clicked.connect(lambda _, lid=lot.id: self._show_detail(lid))
                    bl.addWidget(view_btn)

                    # Next Stage
                    next_st = NEXT_STAGE.get(lot.current_stage)

                    if next_st:
                        adv_color = STAGE_COLORS.get(next_st, "#2D4A2D")
                        adv_btn = _act_btn(f"→ {next_st}", adv_color, adv_color, w=120)
                        adv_btn.clicked.connect(lambda _, l=lot, ns=next_st: self._advance(l, ns))
                        bl.addWidget(adv_btn)

                    # Scrap
                    if lot.current_stage != STAGE_SCRAP:
                        sc_btn = _act_btn("Scrap", "#C0392B", "#E74C3C", w=60)
                        sc_btn.clicked.connect(lambda _, l=lot: self._scrap(l))
                        bl.addWidget(sc_btn)

                    # --- CHANGED HERE: Custom button ONLY for the Hardening stage ---
                    if lot.current_stage == STAGE_HARDENING:
                        process_btn = _act_btn("Process", "#D35400", "#E67E22", w=75)
                        process_btn.clicked.connect(lambda _, l=lot: self._custom_process(l))
                        bl.addWidget(process_btn)
                    # ----------------------------------------------------------------

                    # Ensure we use the dynamic action_col here
                    self.table.setCellWidget(row, action_col, bw)

            fit_table_columns_to_contents(self.table, self._column_min_widths)

        except Exception as e:
            self.table.setRowCount(1)
            err = QTableWidgetItem(f"⚠  {e}")
            err.setForeground(QColor("#C0392B"))
            self.table.setItem(0, 0, err)


    def _show_detail(self, lot_id):
        dlg = LotDetailDialog(lot_id, parent=self)
        dlg.exec()

    def _advance(self, lot, next_stage):
        dlg = AdvanceStageDialog(lot, next_stage, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        from services.user_service import ProductionService
        from models.user_model import ProductionStage

        # Stage-specific handling
        if next_stage == STAGE_GERMINATION:
            stage = ProductionStage(
                lot_id=lot.id,
                stage=STAGE_GERMINATION,
                stage_date=datetime.now(),
                seed_quantity=dlg.seed_qty_spin.value(),
                location=dlg.location_edit.text().strip(),
                done_by=dlg.done_by_edit.text().strip(),
                notes=dlg.notes_edit.toPlainText().strip(),
            )

        elif next_stage == STAGE_TRANSPLANTING:
            # Auto-calc plants from tray type metadata
            TRAY_METADATA = {"104-cell": 104, "198-cell": 198, "160-cell": 160, "67-cell": 67}
            tray_type = dlg.tray_type_combo.currentText().strip()
            tray_count = dlg.tray_spin.value()
            plants_per_tray = TRAY_METADATA.get(tray_type, 0)
            total_plants = tray_count * plants_per_tray

            stage = ProductionStage(
                lot_id=lot.id,
                stage=STAGE_TRANSPLANTING,
                stage_date=datetime.now(),
                quantity_in=lot.current_quantity,
                quantity_out=total_plants,
                tray_count=tray_count,
                tray_type=tray_type,
                location=dlg.location_edit.text().strip(),
                done_by=dlg.done_by_edit.text().strip(),
                notes=dlg.notes_edit.toPlainText().strip(),
            )

        elif next_stage == STAGE_HARDENING:
            stage = ProductionStage(
                lot_id=lot.id,
                stage=STAGE_HARDENING,
                stage_date=datetime.now(),
                quantity_in=lot.current_quantity,
                quantity_out=lot.current_quantity,
                price=dlg.price_spin.value(),
                location=dlg.location_edit.text().strip(),
                done_by=dlg.done_by_edit.text().strip(),
                notes=dlg.notes_edit.toPlainText().strip(),
            )

        ProductionService.add_stage(stage)

    def _scrap(self, lot):
        dlg = ScrapDialog(
            lot,
            parent=self
        )

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            from services.user_service import ProductionService
            from backend.realtime import db_signals

            ProductionService.record_scrap(
                lot_id=lot.id,
                stage_id=lot.stages[-1].id
                if lot.stages else None,
                quantity=dlg.qty_spin.value(),
                reason=dlg.reason_combo.currentText(),
                notes=dlg.notes_edit.toPlainText().strip(),
                recorded_by=dlg.by_edit.text().strip(),
            )

            db_signals.plants_changed.emit(
                "production"
            )

            QMessageBox.information(
                self,
                "Scrap Recorded",
                f"❌ {dlg.qty_spin.value()} plants "
                f"scrapped from "
                f"{lot.lot_number}."
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                str(e)
            )

    # --- CHANGED HERE: Added placeholder function for the new Process button ---
    def _custom_process(self, lot):
        # This function runs when the user clicks the "Process" button in the Hardening tab.
        # You can replace this popup with your custom logic, dialog box, or database update!
        QMessageBox.information(
            self,
            "Process Lot",
            f"Ready to process lot {lot.lot_number} (Currently in Hardening).\n\n"
            f"Current Quantity: {lot.current_quantity}\n\n"
            f"Add your custom processing logic here!"
        )
    # ---------------------------------------------------------------------------


# ─────────────────────────────────────────────────────────────────────────────
#  Main Production Page
# ─────────────────────────────────────────────────────────────────────────────

class ProductionPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("ProductionPage{background:#F4F8F1;}" + TABLE_STYLE)

        main = QVBoxLayout(self)
        main.setContentsMargins(32, 28, 32, 28)
        main.setSpacing(16)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        tc  = QVBoxLayout(); tc.setSpacing(2)
        title = QLabel("Production")
        title.setStyleSheet("font-size:28px;font-weight:bold;color:#1A3A1A;")
        sub = QLabel("Track plant lots: Germination → Transplanting → Hardening (Stays here) → Scrap")
        sub.setStyleSheet("font-size:13px;color:#7A9A7A;")
        tc.addWidget(title); tc.addWidget(sub)
        hdr.addLayout(tc); hdr.addStretch()

        new_btn = QPushButton("＋  New Lot  (1st Entry)")
        new_btn.setFixedHeight(40)
        new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_btn.setStyleSheet(
            "QPushButton{background:#1E5C1E;color:white;border:none;"
            "border-radius:8px;padding:0 22px;font-size:14px;font-weight:bold;}"
            "QPushButton:hover{background:#2E7D2E;}"
        )
        new_btn.clicked.connect(self._new_lot)
        hdr.addWidget(new_btn)
        main.addLayout(hdr)

        # ── Stage flow strip ──────────────────────────────────────────────────
        flow = QHBoxLayout(); flow.setSpacing(6)
        for i, stage in enumerate(STAGE_ORDER):
            lbl = QLabel(f"  {stage}  ")
            lbl.setStyleSheet(
                f"background:{STAGE_COLORS[stage]};color:white;border-radius:10px;"
                f"font-size:12px;font-weight:bold;padding:5px 12px;"
            )
            flow.addWidget(lbl)
            if i < len(STAGE_ORDER) - 1:
                arr = QLabel("→")
                arr.setStyleSheet("font-size:16px;color:#AAAAAA;")
                flow.addWidget(arr)
        flow.addStretch()
        main.addLayout(flow)

        # ── Tabs ──────────────────────────────────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self._all_tab    = LotTableWidget("")
        self._germ_tab   = LotTableWidget(STAGE_GERMINATION)
        self._trans_tab  = LotTableWidget(STAGE_TRANSPLANTING)
        self._hard_tab   = LotTableWidget(STAGE_HARDENING)
        self._scrap_tab  = LotTableWidget(STAGE_SCRAP)

        self.tabs.addTab(self._all_tab,   "📋  All Lots")
        self.tabs.addTab(self._germ_tab,  "🌱  Germination")
        self.tabs.addTab(self._trans_tab, "🌿  Transplanting")
        self.tabs.addTab(self._hard_tab,  "🪴  Hardening (Processing)")
        self.tabs.addTab(self._scrap_tab, "❌  Scrap")

        main.addWidget(self.tabs)

        # Real-time signals
        db_signals.plants_changed.connect(self._on_db_change)

    def _on_db_change(self, payload: str = ""):
        tab = self.tabs.currentWidget()
        if hasattr(tab, 'load'):
            tab.load()

    def _new_lot(self):
        dlg = NewLotDialog(parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            from services.user_service import ProductionService
            from models.user_model import ProductionLot, ProductionStage

            if not dlg.plant_edit.text().strip():
                QMessageBox.warning(self, "Validation", "Plant name is required.")
                return

            # Create lot with only Germination fields
            lot = ProductionLot(
                lot_number=dlg._lot_number,
                plant_name=dlg.plant_edit.text().strip(),
                variety=dlg.variety_edit.text().strip(),
                seed_quantity=dlg.seed_qty_spin.value(),
                location=dlg.location_edit.text().strip(),
                created_by=dlg.by_edit.text().strip(),
                notes=dlg.notes_edit.toPlainText().strip(),
                # Germination stage → no trays/plants yet
                quantity=0,
                tray_count=0,
                plants_per_tray=0,
                tray_type=""
            )
            lot = ProductionService.create_lot(lot)

            # Auto-create first stage (Germination)
            stage = ProductionStage(
                lot_id=lot.id,
                stage=STAGE_GERMINATION,
                stage_date=datetime.now(),
                quantity_in=0,  # no plants yet, only seeds
                quantity_out=0,
                tray_count=0,
                location=lot.location,
                done_by=lot.created_by,
                notes="Initial germination entry (seed quantity recorded).",
            )
            ProductionService.add_stage(stage)

            # Refresh tabs
            for tab in [self._all_tab, self._germ_tab]:
                tab.load()

            QMessageBox.information(
                self, "Lot Created",
                f"✅ Lot {lot.lot_number} created.\n"
                f"Plant: {lot.plant_name}   Seed Qty: {lot.seed_quantity} grams\n\n"
                f"Lot is now in Germination stage."
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
