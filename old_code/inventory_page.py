"""
Inventory Page — 3 tabs:
  1. Plants   — with tray/bucket container stock + loose plant stock
  2. Seeds    — seed inventory in grams + packets
  3. Containers — tray/bucket/pot stock management
"""
from frontend.filter_bar import FilterBar
from backend.realtime import db_signals
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QDialog, QFormLayout, QSpinBox, QDoubleSpinBox,
    QTextEdit, QMessageBox, QHeaderView, QSizePolicy, QTabWidget, QComboBox,
    QFrame, QGroupBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QFont

# ── Shared styles ─────────────────────────────────────────────────────────────
TABLE_STYLE = """
QWidget { font-family:'Segoe UI',Arial,sans-serif; }
QTabWidget::pane { border:none; background:#F5F7F2; }
QTabBar::tab {
    background:#E8EDE8; color:#2D4A2D;
    border:none; border-radius:8px 8px 0 0;
    padding:10px 24px; font-size:13px; font-weight:bold; margin-right:4px;
}
QTabBar::tab:selected { background:#2D4A2D; color:white; }
QTabBar::tab:hover    { background:#C8DFC0; }
QTableWidget {
    background:white; border-radius:10px; border:1px solid #D8E8D0;
    gridline-color:#EEF5EA; font-size:13px; outline:none;
}
QTableWidget::item { padding:0 12px; color:#1A3A1A; border:none; }
QTableWidget::item:selected { background:#D6EDD6; color:#1A3A1A; }
QTableWidget::item:hover    { background:#EEF8EE; }
QHeaderView::section {
    background:#EAF3E4; color:#2D5A2D; font-weight:bold; font-size:12px;
    border:none; border-bottom:2px solid #C8DFC0; padding:10px 12px;
}
QLineEdit#search {
    border:1.5px solid #C8DFC0; border-radius:8px;
    padding:8px 14px; font-size:13px; background:white; color:#1A3A1A;
}
QLineEdit#search:focus { border:1.5px solid #4A7C4A; }
"""

DIALOG_STYLE = """
QDialog { background:#F7FAF5; }
QGroupBox {
    border:1.5px solid #C8DFC0; border-radius:8px;
    margin-top:10px; font-weight:bold; color:#2D4A2D; font-size:13px;
}
QGroupBox::title { subcontrol-origin:margin; left:10px; padding:0 4px; }
QLabel  { font-size:13px; color:#2D4A2D; font-weight:500; }
QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    border:1.5px solid #C8DFC0; border-radius:6px;
    padding:7px 11px; font-size:13px; background:white; color:#1A3A1A;
}
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus,
QDoubleSpinBox:focus, QComboBox:focus { border:1.5px solid #4A7C4A; }
"""

def _btn(text, bg, hover, w=85, h=34):
    b = QPushButton(text)
    b.setFixedSize(QSize(w, h))
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setStyleSheet(
        f"QPushButton{{background:{bg};color:white;font-size:12px;"
        f"font-weight:bold;border:none;border-radius:6px;}}"
        f"QPushButton:hover{{background:{hover};}}"
    )
    return b

def _header_bar(title, sub, btn_label, btn_cb, search_cb=None):
    outer = QVBoxLayout(); outer.setSpacing(10)
    row = QHBoxLayout()
    tc  = QVBoxLayout()
    t   = QLabel(title); t.setStyleSheet("font-size:24px;font-weight:bold;color:#1A3A1A;")
    s   = QLabel(sub);   s.setStyleSheet("font-size:12px;color:#7A9A7A;")
    tc.addWidget(t); tc.addWidget(s); row.addLayout(tc); row.addStretch()
    if search_cb:
        se = QLineEdit(); se.setObjectName("search")
        se.setPlaceholderText("🔍  Search…"); se.setFixedSize(220,36)
        se.textChanged.connect(search_cb); row.addWidget(se)
        row.addSpacing(8)
    add = QPushButton(btn_label)
    add.setFixedHeight(36)
    add.setCursor(Qt.CursorShape.PointingHandCursor)
    add.setStyleSheet(
        "QPushButton{background:#2D4A2D;color:white;border:none;"
        "border-radius:8px;padding:0 20px;font-size:13px;font-weight:bold;}"
        "QPushButton:hover{background:#3D6B3D;}"
    )
    add.clicked.connect(btn_cb); row.addWidget(add)
    outer.addLayout(row)
    return outer, se if search_cb else None


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 1 — Plants
# ─────────────────────────────────────────────────────────────────────────────
class PlantDialog(QDialog):
    def __init__(self, plant=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Plant" if not plant else "Edit Plant")
        self.setMinimumWidth(520)
        self.setStyleSheet(DIALOG_STYLE)

        lay = QVBoxLayout(self); lay.setContentsMargins(28,24,28,24); lay.setSpacing(12)
        title = QLabel("Add Plant" if not plant else f"Edit — {plant.name}")
        title.setStyleSheet("font-size:18px;font-weight:bold;color:#1E3A1E;")
        lay.addWidget(title)

        # ── Basic info ──────────────────────────────────────────────────────
        basic = QGroupBox("🪴  Plant Details")
        bf = QFormLayout(basic); bf.setSpacing(10)
        self.name_edit  = QLineEdit(); self.name_edit.setPlaceholderText("e.g. Money Plant")
        self.cat_edit   = QLineEdit(); self.cat_edit.setPlaceholderText("e.g. Indoor, Flowering")
        self.desc_edit  = QTextEdit(); self.desc_edit.setFixedHeight(60)
        self.price_spin = QDoubleSpinBox(); self.price_spin.setMaximum(999999); self.price_spin.setPrefix("₹ ")
        self.stock_spin = QSpinBox(); self.stock_spin.setMaximum(999999)
        self.thresh_spin= QSpinBox(); self.thresh_spin.setMaximum(99999); self.thresh_spin.setValue(10)
        bf.addRow("Name *",       self.name_edit)
        bf.addRow("Category",     self.cat_edit)
        bf.addRow("Description",  self.desc_edit)
        bf.addRow("Price/plant",  self.price_spin)
        bf.addRow("Loose Stock",  self.stock_spin)
        bf.addRow("Alert Below",  self.thresh_spin)
        lay.addWidget(basic)

        # ── Container / tray info ───────────────────────────────────────────
        cont = QGroupBox("📦  Container / Tray Info  (optional)")
        cf = QFormLayout(cont); cf.setSpacing(10)
        self.ctype_combo = QComboBox()
        self.ctype_combo.addItems(["None", "Tray", "Bucket", "Pot", "Box", "Basket", "Other"])
        self.ppu_spin  = QSpinBox(); self.ppu_spin.setMinimum(1); self.ppu_spin.setMaximum(9999)
        self.ppu_spin.setValue(1); self.ppu_spin.setToolTip("Plants per tray/bucket")
        self.cs_spin   = QSpinBox(); self.cs_spin.setMaximum(99999)
        cf.addRow("Container Type",      self.ctype_combo)
        cf.addRow("Plants per Unit",     self.ppu_spin)
        cf.addRow("No. of Units in Stock", self.cs_spin)
        self._cont_note = QLabel("Total plants = Loose Stock + (Units × Plants/Unit)")
        self._cont_note.setStyleSheet("font-size:11px;color:#4A7C4A;font-style:italic;")
        cf.addRow("", self._cont_note)
        lay.addWidget(cont)

        if plant:
            self.name_edit.setText(plant.name)
            self.cat_edit.setText(plant.category or "")
            self.desc_edit.setPlainText(plant.description or "")
            self.price_spin.setValue(float(plant.unit_price))
            self.stock_spin.setValue(plant.stock_qty)
            self.thresh_spin.setValue(plant.low_stock_threshold)
            ct = getattr(plant, "container_type", "") or "None"
            idx = self.ctype_combo.findText(ct)
            self.ctype_combo.setCurrentIndex(idx if idx >= 0 else 0)
            self.ppu_spin.setValue(getattr(plant, "plants_per_unit", 1) or 1)
            self.cs_spin.setValue(getattr(plant, "container_stock", 0) or 0)

        btns = QHBoxLayout(); btns.setSpacing(10)
        c_btn = QPushButton("Cancel"); c_btn.setFixedHeight(38)
        c_btn.setStyleSheet("QPushButton{background:#E8EDE8;color:#2D4A2D;border:none;border-radius:7px;padding:0 20px;font-size:13px;}")
        s_btn = QPushButton("Save Plant"); s_btn.setFixedHeight(38)
        s_btn.setStyleSheet("QPushButton{background:#2D4A2D;color:white;border:none;border-radius:7px;padding:0 24px;font-size:13px;font-weight:bold;}QPushButton:hover{background:#3D6B3D;}")
        c_btn.clicked.connect(self.reject); s_btn.clicked.connect(self.accept)
        btns.addStretch(); btns.addWidget(c_btn); btns.addWidget(s_btn)
        lay.addLayout(btns)


class StockAdjustDialog(QDialog):
    """Quick +/- stock for trays or loose plants."""
    def __init__(self, plant, parent=None):
        super().__init__(parent)
        self.plant = plant
        self.setWindowTitle(f"Adjust Stock — {plant.name}")
        self.setFixedWidth(400)
        self.setStyleSheet(DIALOG_STYLE)
        lay = QVBoxLayout(self); lay.setContentsMargins(28,24,28,24); lay.setSpacing(14)

        title = QLabel(f"📦  {plant.name}")
        title.setStyleSheet("font-size:16px;font-weight:bold;color:#1E3A1E;")
        lay.addWidget(title)

        ct = getattr(plant, "container_type", "") or "None"
        ppu = getattr(plant, "plants_per_unit", 1) or 1
        cs  = getattr(plant, "container_stock", 0) or 0

        # Current stock summary
        info = QLabel(
            f"Loose plants: {plant.stock_qty}\n"
            + (f"Container ({ct}): {cs} units  ×  {ppu} plants = {cs*ppu} plants\n" if ct not in ("","None") else "")
            + f"Total: {plant.total_plants} plants"
        )
        info.setStyleSheet("background:#EAF3E4;border-radius:8px;padding:10px;font-size:13px;color:#1A3A1A;")
        lay.addWidget(info)

        form = QFormLayout(); form.setSpacing(10)

        # Loose plants
        self.loose_spin = QSpinBox(); self.loose_spin.setRange(-99999, 99999)
        self.loose_spin.setValue(0)
        self.loose_spin.setToolTip("Positive = add, Negative = remove")
        form.addRow("Add/Remove Plants (+/-)", self.loose_spin)

        # Containers
        if ct not in ("", "None"):
            self.tray_spin = QSpinBox(); self.tray_spin.setRange(-99999, 99999)
            self.tray_spin.setValue(0)
            self.tray_spin.setToolTip(f"Positive = add {ct}s, Negative = remove")
            form.addRow(f"Add/Remove {ct}s (+/-)", self.tray_spin)
        else:
            self.tray_spin = None

        lay.addLayout(form)

        note = QLabel("Tip: Use negative numbers to remove stock.")
        note.setStyleSheet("font-size:11px;color:#7A9A7A;font-style:italic;")
        lay.addWidget(note)

        btns = QHBoxLayout(); btns.setSpacing(10)
        c = QPushButton("Cancel"); c.setFixedHeight(38)
        c.setStyleSheet("QPushButton{background:#E8EDE8;color:#2D4A2D;border:none;border-radius:7px;padding:0 20px;}")
        s = QPushButton("Apply"); s.setFixedHeight(38)
        s.setStyleSheet("QPushButton{background:#1E5C1E;color:white;border:none;border-radius:7px;padding:0 24px;font-weight:bold;}QPushButton:hover{background:#2E7D2E;}")
        c.clicked.connect(self.reject); s.clicked.connect(self.accept)
        btns.addStretch(); btns.addWidget(c); btns.addWidget(s)
        lay.addLayout(btns)


class PlantsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(TABLE_STYLE)
        lay = QVBoxLayout(self); lay.setContentsMargins(0,12,0,0); lay.setSpacing(14)

        hdr, _ = _header_bar(
            "🪴  Plants Inventory",
            "Manage plant stock — loose plants and tray/bucket containers",
            "＋  Add Plant", self.add_plant
        )
        lay.addLayout(hdr)
        self.filter_bar = FilterBar(
            columns=["Name","Category","Container Type"],
            auto_refresh_sec=5,
        )
        self.filter_bar.filter_changed.connect(lambda s,c,d: self.load_data())
        self.filter_bar.refresh_requested.connect(self.load_data)
        lay.addWidget(self.filter_bar)

        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "ID", "Plant Name", "Category", "Price",
            "Loose\nStock", "Container", "Units", "Plants/Unit", "Actions"
        ])
        hh = self.table.horizontalHeader()
        for col, mode, w in [
            (0, QHeaderView.ResizeMode.Fixed,   50),
            (1, QHeaderView.ResizeMode.Stretch, 0),
            (2, QHeaderView.ResizeMode.Stretch, 0),
            (3, QHeaderView.ResizeMode.Fixed,   90),
            (4, QHeaderView.ResizeMode.Fixed,   70),
            (5, QHeaderView.ResizeMode.Fixed,  100),
            (6, QHeaderView.ResizeMode.Fixed,   65),
            (7, QHeaderView.ResizeMode.Fixed,   80),
            (8, QHeaderView.ResizeMode.Fixed,  230),
        ]:
            hh.setSectionResizeMode(col, mode)
            if w: self.table.setColumnWidth(col, w)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(TABLE_STYLE + "QTableWidget{alternate-background-color:#F5FAF3;}")
        lay.addWidget(self.table)

        # ── Real-time updates ────────────────────────────────────────────────
        db_signals.plants_changed.connect(self._on_db_change)
        self.load_data()

    def _ci(self, text, bold=False, color=None):
        it = QTableWidgetItem(str(text))
        it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        if bold: f=it.font(); f.setBold(True); it.setFont(f)
        if color: it.setForeground(QColor(color))
        return it

    def load_data(self):
        try:
            from services.user_service import PlantService
            all_plants = PlantService.get_all()
            q   = self.filter_bar.get_search()
            col = self.filter_bar.get_column()
            if q:
                ql = q.lower()
                def pm(p):
                    fields = [p.name, p.category or "",
                              getattr(p,"container_type","") or ""]
                    if col == 0: return any(ql in f.lower() for f in fields)
                    elif col <= len(fields): return ql in fields[col-1].lower()
                    return True
                plants = [p for p in all_plants if pm(p)]
            else:
                plants = all_plants
            self.filter_bar.set_count(len(plants), len(all_plants))
            self.table.setRowCount(0); self.table.setRowCount(len(plants))
            for row, p in enumerate(plants):
                self.table.setRowHeight(row, 54)
                ct  = getattr(p,"container_type","") or "—"
                ppu = getattr(p,"plants_per_unit",1) or 1
                cs  = getattr(p,"container_stock",0) or 0
                self.table.setItem(row, 0, self._ci(str(p.id or "")))
                ni = QTableWidgetItem(str(p.name or ""))
                ni.setFont(QFont("Segoe UI",13,QFont.Weight.Medium))
                self.table.setItem(row, 1, ni)
                self.table.setItem(row, 2, QTableWidgetItem(str(p.category or "")))
                self.table.setItem(row, 3, self._ci(f"₹{float(p.unit_price):.0f}"))
                # Loose stock — red if low
                si = self._ci(str(p.stock_qty))
                if p.is_low_stock:
                    si.setForeground(QColor("#C0392B")); f=si.font(); f.setBold(True); si.setFont(f)
                self.table.setItem(row, 4, si)
                # Container
                ctype_item = self._ci(ct if ct != "—" else "None")
                if ct not in ("—","None",""):
                    ctype_item.setForeground(QColor("#2980B9"))
                self.table.setItem(row, 5, ctype_item)
                self.table.setItem(row, 6, self._ci(str(cs) if ct not in ("—","None","") else "—"))
                self.table.setItem(row, 7, self._ci(str(ppu) if ct not in ("—","None","") else "—"))

                # Actions
                bw = QWidget(); bw.setStyleSheet("background:transparent;")
                bl = QHBoxLayout(bw); bl.setContentsMargins(6,5,6,5); bl.setSpacing(6)
                bl.setAlignment(Qt.AlignmentFlag.AlignVCenter|Qt.AlignmentFlag.AlignLeft)

                adj  = _btn("± Stock", "#1A5276","#2471A3", w=72)
                edit = _btn("Edit",    "#2E7D32","#43A047", w=60)
                dlt  = _btn("Delete",  "#C62828","#EF5350", w=65)

                adj.clicked.connect(lambda _,pl=p: self.adjust_stock(pl))
                edit.clicked.connect(lambda _,pl=p: self.edit_plant(pl))
                dlt.clicked.connect(lambda _,pid=p.id: self.delete_plant(pid))
                bl.addWidget(adj); bl.addWidget(edit); bl.addWidget(dlt)
                self.table.setCellWidget(row, 8, bw)
        except Exception as e:
            self.table.setRowCount(1)
            err = QTableWidgetItem(f"⚠  {e}")
            err.setForeground(QColor("#C0392B"))
            self.table.setItem(0,0,err)

    def add_plant(self):
        dlg = PlantDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                from services.user_service import PlantService
                from models.user_model import Plant
                ct = dlg.ctype_combo.currentText()
                p = Plant(
                    name=dlg.name_edit.text().strip(),
                    category=dlg.cat_edit.text().strip(),
                    description=dlg.desc_edit.toPlainText().strip(),
                    unit_price=dlg.price_spin.value(),
                    stock_qty=dlg.stock_spin.value(),
                    low_stock_threshold=dlg.thresh_spin.value(),
                    container_type=ct if ct != "None" else "",
                    plants_per_unit=dlg.ppu_spin.value(),
                    container_stock=dlg.cs_spin.value(),
                )
                if not p.name:
                    QMessageBox.warning(self,"Validation","Plant name is required."); return
                PlantService.save(p); self.load_data()
            except Exception as e:
                QMessageBox.critical(self,"Error",str(e))

    def edit_plant(self, plant):
        dlg = PlantDialog(plant=plant, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                from services.user_service import PlantService
                ct = dlg.ctype_combo.currentText()
                plant.name             = dlg.name_edit.text().strip()
                plant.category         = dlg.cat_edit.text().strip()
                plant.description      = dlg.desc_edit.toPlainText().strip()
                plant.unit_price       = dlg.price_spin.value()
                plant.stock_qty        = dlg.stock_spin.value()
                plant.low_stock_threshold = dlg.thresh_spin.value()
                plant.container_type   = ct if ct != "None" else ""
                plant.plants_per_unit  = dlg.ppu_spin.value()
                plant.container_stock  = dlg.cs_spin.value()
                PlantService.save(plant); self.load_data()
            except Exception as e:
                QMessageBox.critical(self,"Error",str(e))

    def adjust_stock(self, plant):
        dlg = StockAdjustDialog(plant, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                from services.user_service import PlantService
                from models.user_model import Plant
                loose_delta = dlg.loose_spin.value()
                tray_delta  = dlg.tray_spin.value() if dlg.tray_spin else 0
                new_loose = max(0, plant.stock_qty + loose_delta)
                new_cs    = max(0, (getattr(plant,"container_stock",0) or 0) + tray_delta)
                plant.stock_qty      = new_loose
                plant.container_stock= new_cs
                PlantService.save(plant)
                self.load_data()
                ppu = getattr(plant,"plants_per_unit",1) or 1
                QMessageBox.information(self,"Stock Updated",
                    f"Updated stock for {plant.name}:\n"
                    f"  Loose plants: {new_loose}\n"
                    f"  Container units: {new_cs}  (× {ppu} = {new_cs*ppu} plants)\n"
                    f"  Total: {new_loose + new_cs*ppu} plants"
                )
            except Exception as e:
                QMessageBox.critical(self,"Error",str(e))

    def delete_plant(self, pid):
        if QMessageBox.question(self,"Confirm","Delete this plant? Cannot be undone.",
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            try:
                from services.user_service import PlantService
                PlantService.delete(pid); self.load_data()
            except Exception as e:
                QMessageBox.critical(self,"Error",str(e))


    def _on_db_change(self, payload: str = ""):
        """Called instantly when any table changes on any connected machine."""
        self.load_data()


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 2 — Seeds
# ─────────────────────────────────────────────────────────────────────────────
class SeedDialog(QDialog):
    def __init__(self, seed=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Seed" if not seed else "Edit Seed")
        self.setMinimumWidth(500)
        self.setStyleSheet(DIALOG_STYLE)
        lay = QVBoxLayout(self); lay.setContentsMargins(28,24,28,24); lay.setSpacing(12)

        title = QLabel("Add Seed" if not seed else f"Edit — {seed.name}")
        title.setStyleSheet("font-size:18px;font-weight:bold;color:#1E3A1E;")
        lay.addWidget(title)

        basic = QGroupBox("🌱  Seed Details")
        bf = QFormLayout(basic); bf.setSpacing(10)
        self.name_edit     = QLineEdit(); self.name_edit.setPlaceholderText("e.g. Tomato Seeds")
        self.variety_edit  = QLineEdit(); self.variety_edit.setPlaceholderText("e.g. Cherry, Roma")
        self.supplier_edit = QLineEdit(); self.supplier_edit.setPlaceholderText("Supplier name")
        self.notes_edit    = QTextEdit(); self.notes_edit.setFixedHeight(55)
        self.germ_spin     = QDoubleSpinBox(); self.germ_spin.setRange(0,100); self.germ_spin.setSuffix(" %")
        bf.addRow("Name *",        self.name_edit)
        bf.addRow("Variety",       self.variety_edit)
        bf.addRow("Supplier",      self.supplier_edit)
        bf.addRow("Germination %", self.germ_spin)
        bf.addRow("Notes",         self.notes_edit)
        lay.addWidget(basic)

        stock = QGroupBox("📦  Stock & Pricing")
        sf = QFormLayout(stock); sf.setSpacing(10)
        self.grams_spin      = QDoubleSpinBox(); self.grams_spin.setMaximum(9999999); self.grams_spin.setSuffix(" g")
        self.packets_spin    = QSpinBox();        self.packets_spin.setMaximum(999999)
        self.gpp_spin        = QDoubleSpinBox();  self.gpp_spin.setMaximum(9999); self.gpp_spin.setSuffix(" g/pkt")
        self.price_g_spin    = QDoubleSpinBox();  self.price_g_spin.setMaximum(999999); self.price_g_spin.setPrefix("₹ "); self.price_g_spin.setSuffix("/g")
        self.price_pkt_spin  = QDoubleSpinBox();  self.price_pkt_spin.setMaximum(999999); self.price_pkt_spin.setPrefix("₹ "); self.price_pkt_spin.setSuffix("/pkt")
        self.low_grams_spin  = QDoubleSpinBox();  self.low_grams_spin.setMaximum(999999); self.low_grams_spin.setValue(100); self.low_grams_spin.setSuffix(" g")
        sf.addRow("Stock (grams)",      self.grams_spin)
        sf.addRow("Stock (packets)",    self.packets_spin)
        sf.addRow("Grams per packet",   self.gpp_spin)
        sf.addRow("Price per gram",     self.price_g_spin)
        sf.addRow("Price per packet",   self.price_pkt_spin)
        sf.addRow("Alert below (g)",    self.low_grams_spin)
        lay.addWidget(stock)

        if seed:
            self.name_edit.setText(seed.name)
            self.variety_edit.setText(seed.variety or "")
            self.supplier_edit.setText(seed.supplier or "")
            self.notes_edit.setPlainText(seed.notes or "")
            self.germ_spin.setValue(float(seed.germination_rate or 0))
            self.grams_spin.setValue(float(seed.quantity_grams or 0))
            self.packets_spin.setValue(seed.quantity_packets or 0)
            self.gpp_spin.setValue(float(seed.grams_per_packet or 0))
            self.price_g_spin.setValue(float(seed.unit_price_gram or 0))
            self.price_pkt_spin.setValue(float(seed.unit_price_packet or 0))
            self.low_grams_spin.setValue(float(seed.low_stock_grams or 100))

        btns = QHBoxLayout(); btns.setSpacing(10)
        c = QPushButton("Cancel"); c.setFixedHeight(38)
        c.setStyleSheet("QPushButton{background:#E8EDE8;color:#2D4A2D;border:none;border-radius:7px;padding:0 20px;}")
        s = QPushButton("Save Seed"); s.setFixedHeight(38)
        s.setStyleSheet("QPushButton{background:#2D4A2D;color:white;border:none;border-radius:7px;padding:0 24px;font-weight:bold;}QPushButton:hover{background:#3D6B3D;}")
        c.clicked.connect(self.reject); s.clicked.connect(self.accept)
        btns.addStretch(); btns.addWidget(c); btns.addWidget(s)
        lay.addLayout(btns)


# class SeedStockDialog(QDialog):
#     def __init__(self, seed, parent=None):
#         super().__init__(parent)
#         self.setWindowTitle(f"Adjust Stock — {seed.name}")
#         self.setFixedWidth(380)
#         self.setStyleSheet(DIALOG_STYLE)
#         lay = QVBoxLayout(self); lay.setContentsMargins(28,24,28,24); lay.setSpacing(14)
#
#         QLabel(f"🌱  {seed.name}").setParent(self)
#         title = QLabel(f"🌱  {seed.name}")
#         title.setStyleSheet("font-size:16px;font-weight:bold;color:#1E3A1E;")
#         lay.addWidget(title)
#         info = QLabel(f"Current stock:\n  Grams: {float(seed.quantity_grams):.1f} g\n  Packets: {seed.quantity_packets}")
#         info.setStyleSheet("background:#EAF3E4;border-radius:8px;padding:10px;font-size:13px;color:#1A3A1A;")
#         lay.addWidget(info)
#
#         form = QFormLayout(); form.setSpacing(10)
#         self.grams_spin   = QDoubleSpinBox(); self.grams_spin.setRange(-999999,999999); self.grams_spin.setSuffix(" g")
#         self.packets_spin = QSpinBox();        self.packets_spin.setRange(-999999,999999)
#         form.addRow("Add/Remove Grams (+/-)",   self.grams_spin)
#         form.addRow("Add/Remove Packets (+/-)", self.packets_spin)
#         lay.addLayout(form)
#         note = QLabel("Use negative to remove stock.")
#         note.setStyleSheet("font-size:11px;color:#7A9A7A;font-style:italic;")
#         lay.addWidget(note)
#
#         btns = QHBoxLayout(); btns.setSpacing(10)
#         c = QPushButton("Cancel"); c.setFixedHeight(38)
#         c.setStyleSheet("QPushButton{background:#E8EDE8;color:#2D4A2D;border:none;border-radius:7px;padding:0 20px;}")
#         s = QPushButton("Apply"); s.setFixedHeight(38)
#         s.setStyleSheet("QPushButton{background:#1E5C1E;color:white;border:none;border-radius:7px;padding:0 24px;font-weight:bold;}QPushButton:hover{background:#2E7D2E;}")
#         c.clicked.connect(self.reject); s.clicked.connect(self.accept)
#         btns.addStretch(); btns.addWidget(c); btns.addWidget(s)
#         lay.addLayout(btns)
#
#
# class SeedsTab(QWidget):
#     def __init__(self):
#         super().__init__()
#         self.setStyleSheet(TABLE_STYLE)
#         lay = QVBoxLayout(self); lay.setContentsMargins(0,12,0,0); lay.setSpacing(14)
#
#         hdr, _ = _header_bar(
#             "🌱  Seeds Inventory",
#             "Track seed stock by grams and packets",
#             "＋  Add Seed", self.add_seed
#         )
#         lay.addLayout(hdr)
#         self.filter_bar = FilterBar(
#             columns=["Name","Variety","Supplier"],
#             auto_refresh_sec=5,
#         )
#         self.filter_bar.filter_changed.connect(lambda s,c,d: self.load_data())
#         self.filter_bar.refresh_requested.connect(self.load_data)
#         lay.addWidget(self.filter_bar)
#
#         self.table = QTableWidget()
#         self.table.setColumnCount(9)
#         self.table.setHorizontalHeaderLabels([
#             "ID","Seed Name","Variety","Supplier",
#             "Stock (g)","Packets","Price/g","Price/pkt","Actions"
#         ])
#         hh = self.table.horizontalHeader()
#         for col, mode, w in [
#             (0,QHeaderView.ResizeMode.Fixed,50),
#             (1,QHeaderView.ResizeMode.Stretch,0),
#             (2,QHeaderView.ResizeMode.Stretch,0),
#             (3,QHeaderView.ResizeMode.Stretch,0),
#             (4,QHeaderView.ResizeMode.Fixed,90),
#             (5,QHeaderView.ResizeMode.Fixed,70),
#             (6,QHeaderView.ResizeMode.Fixed,80),
#             (7,QHeaderView.ResizeMode.Fixed,85),
#             (8,QHeaderView.ResizeMode.Fixed,200),
#         ]:
#             hh.setSectionResizeMode(col, mode)
#             if w: self.table.setColumnWidth(col, w)
#         self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
#         self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
#         self.table.verticalHeader().setVisible(False)
#         self.table.setAlternatingRowColors(True)
#         self.table.setStyleSheet(TABLE_STYLE+"QTableWidget{alternate-background-color:#F5FAF3;}")
#         lay.addWidget(self.table)
#
#         # ── Real-time updates ────────────────────────────────────────────────
#         db_signals.seeds_changed.connect(self._on_db_change)
#         self.load_data()
#
#     def _ci(self, text, color=None):
#         it = QTableWidgetItem(str(text))
#         it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
#         if color: it.setForeground(QColor(color))
#         return it
#
#     def load_data(self):
#         try:
#             from services.user_service import SeedService
#             all_seeds = SeedService.get_all()
#             q   = self.filter_bar.get_search()
#             col = self.filter_bar.get_column()
#             if q:
#                 ql = q.lower()
#                 def sm(s):
#                     fields = [s.name, s.variety or "", s.supplier or ""]
#                     if col == 0: return any(ql in f.lower() for f in fields)
#                     elif col <= len(fields): return ql in fields[col-1].lower()
#                     return True
#                 seeds = [s for s in all_seeds if sm(s)]
#             else:
#                 seeds = all_seeds
#             self.filter_bar.set_count(len(seeds), len(all_seeds))
#             self.table.setRowCount(0); self.table.setRowCount(len(seeds))
#             for row, s in enumerate(seeds):
#                 self.table.setRowHeight(row, 52)
#                 self.table.setItem(row,0,self._ci(str(s.id or "")))
#                 ni = QTableWidgetItem(str(s.name or ""))
#                 ni.setFont(QFont("Segoe UI",13,QFont.Weight.Medium))
#                 self.table.setItem(row,1,ni)
#                 self.table.setItem(row,2,QTableWidgetItem(str(s.variety or "")))
#                 self.table.setItem(row,3,QTableWidgetItem(str(s.supplier or "")))
#                 gc = "#C0392B" if s.is_low_stock else None
#                 self.table.setItem(row,4,self._ci(f"{float(s.quantity_grams):.1f}",gc))
#                 self.table.setItem(row,5,self._ci(str(s.quantity_packets)))
#                 self.table.setItem(row,6,self._ci(f"₹{float(s.unit_price_gram):.2f}"))
#                 self.table.setItem(row,7,self._ci(f"₹{float(s.unit_price_packet):.2f}"))
#
#                 bw = QWidget(); bw.setStyleSheet("background:transparent;")
#                 bl = QHBoxLayout(bw); bl.setContentsMargins(6,5,6,5); bl.setSpacing(6)
#                 bl.setAlignment(Qt.AlignmentFlag.AlignVCenter|Qt.AlignmentFlag.AlignLeft)
#                 adj  = _btn("± Stock","#1A5276","#2471A3",w=72)
#                 edit = _btn("Edit",   "#2E7D32","#43A047",w=60)
#                 dlt  = _btn("Delete", "#C62828","#EF5350",w=65)
#                 adj.clicked.connect(lambda _,sd=s: self.adjust_stock(sd))
#                 edit.clicked.connect(lambda _,sd=s: self.edit_seed(sd))
#                 dlt.clicked.connect(lambda _,sid=s.id: self.delete_seed(sid))
#                 bl.addWidget(adj); bl.addWidget(edit); bl.addWidget(dlt)
#                 self.table.setCellWidget(row,8,bw)
#         except Exception as e:
#             self.table.setRowCount(1)
#             err = QTableWidgetItem(f"⚠  {e}"); err.setForeground(QColor("#C0392B"))
#             self.table.setItem(0,0,err)
#
#     def add_seed(self):
#         dlg = SeedDialog(parent=self)
#         if dlg.exec() == QDialog.DialogCode.Accepted:
#             try:
#                 from services.user_service import SeedService
#                 from models.user_model import Seed
#                 s = Seed(
#                     name=dlg.name_edit.text().strip(),
#                     variety=dlg.variety_edit.text().strip(),
#                     supplier=dlg.supplier_edit.text().strip(),
#                     notes=dlg.notes_edit.toPlainText().strip(),
#                     germination_rate=dlg.germ_spin.value(),
#                     quantity_grams=dlg.grams_spin.value(),
#                     quantity_packets=dlg.packets_spin.value(),
#                     grams_per_packet=dlg.gpp_spin.value(),
#                     unit_price_gram=dlg.price_g_spin.value(),
#                     unit_price_packet=dlg.price_pkt_spin.value(),
#                     low_stock_grams=dlg.low_grams_spin.value(),
#                 )
#                 if not s.name: QMessageBox.warning(self,"Validation","Name required."); return
#                 SeedService.save(s); self.load_data()
#             except Exception as e: QMessageBox.critical(self,"Error",str(e))
#
#     def edit_seed(self, seed):
#         dlg = SeedDialog(seed=seed, parent=self)
#         if dlg.exec() == QDialog.DialogCode.Accepted:
#             try:
#                 from services.user_service import SeedService
#                 seed.name=dlg.name_edit.text().strip(); seed.variety=dlg.variety_edit.text().strip()
#                 seed.supplier=dlg.supplier_edit.text().strip(); seed.notes=dlg.notes_edit.toPlainText().strip()
#                 seed.germination_rate=dlg.germ_spin.value(); seed.quantity_grams=dlg.grams_spin.value()
#                 seed.quantity_packets=dlg.packets_spin.value(); seed.grams_per_packet=dlg.gpp_spin.value()
#                 seed.unit_price_gram=dlg.price_g_spin.value(); seed.unit_price_packet=dlg.price_pkt_spin.value()
#                 seed.low_stock_grams=dlg.low_grams_spin.value()
#                 SeedService.save(seed); self.load_data()
#             except Exception as e: QMessageBox.critical(self,"Error",str(e))
#
#     def adjust_stock(self, seed):
#         dlg = SeedStockDialog(seed, parent=self)
#         if dlg.exec() == QDialog.DialogCode.Accepted:
#             try:
#                 from services.user_service import SeedService
#                 g = dlg.grams_spin.value(); p = dlg.packets_spin.value()
#                 if g >= 0 and p >= 0:
#                     SeedService.add_stock(seed.id, abs(g), abs(p))
#                 else:
#                     SeedService.remove_stock(seed.id, abs(g), abs(p))
#                 self.load_data()
#             except Exception as e: QMessageBox.critical(self,"Error",str(e))
#
#     def delete_seed(self, sid):
#         if QMessageBox.question(self,"Confirm","Delete this seed?",
#                 QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
#             try:
#                 from services.user_service import SeedService
#                 SeedService.delete(sid); self.load_data()
#             except Exception as e: QMessageBox.critical(self,"Error",str(e))
#
#
#     def _on_db_change(self, payload: str = ""):
#         """Called instantly when any table changes on any connected machine."""
#         self.load_data()
#

# ─────────────────────────────────────────────────────────────────────────────
#  TAB 3 — Containers
# ─────────────────────────────────────────────────────────────────────────────
# class ContainerDialog(QDialog):
#     def __init__(self, cont=None, parent=None):
#         super().__init__(parent)
#         self.setWindowTitle("Add Container" if not cont else "Edit Container")
#         self.setFixedWidth(460)
#         self.setStyleSheet(DIALOG_STYLE)
#         lay = QVBoxLayout(self); lay.setContentsMargins(28,24,28,24); lay.setSpacing(14)
#         title = QLabel("Add Container" if not cont else f"Edit — {cont.name}")
#         title.setStyleSheet("font-size:18px;font-weight:bold;color:#1E3A1E;")
#         lay.addWidget(title)
#         form = QFormLayout(); form.setSpacing(12)
#         self.name_edit  = QLineEdit(); self.name_edit.setPlaceholderText("e.g. 50-Cell Seedling Tray")
#         self.type_combo = QComboBox()
#         self.type_combo.addItems(["Tray","Bucket","Pot","Box","Basket","Bag","Other"])
#         self.cap_spin   = QSpinBox(); self.cap_spin.setMaximum(9999); self.cap_spin.setToolTip("No. of plants/cells it holds")
#         self.stock_spin = QSpinBox(); self.stock_spin.setMaximum(99999)
#         self.cost_spin  = QDoubleSpinBox(); self.cost_spin.setMaximum(999999); self.cost_spin.setPrefix("₹ ")
#         self.notes_edit = QLineEdit(); self.notes_edit.setPlaceholderText("Optional notes")
#         form.addRow("Name *",         self.name_edit)
#         form.addRow("Type",           self.type_combo)
#         form.addRow("Capacity (plants)", self.cap_spin)
#         form.addRow("Stock (units)",  self.stock_spin)
#         form.addRow("Cost per unit",  self.cost_spin)
#         form.addRow("Notes",          self.notes_edit)
#         lay.addLayout(form)
#         if cont:
#             self.name_edit.setText(cont.name)
#             idx = self.type_combo.findText(cont.container_type)
#             self.type_combo.setCurrentIndex(idx if idx>=0 else 0)
#             self.cap_spin.setValue(cont.capacity)
#             self.stock_spin.setValue(cont.stock_qty)
#             self.cost_spin.setValue(float(cont.unit_cost))
#             self.notes_edit.setText(cont.notes or "")
#         btns = QHBoxLayout(); btns.setSpacing(10)
#         c = QPushButton("Cancel"); c.setFixedHeight(38)
#         c.setStyleSheet("QPushButton{background:#E8EDE8;color:#2D4A2D;border:none;border-radius:7px;padding:0 20px;}")
#         s = QPushButton("Save"); s.setFixedHeight(38)
#         s.setStyleSheet("QPushButton{background:#2D4A2D;color:white;border:none;border-radius:7px;padding:0 24px;font-weight:bold;}QPushButton:hover{background:#3D6B3D;}")
#         c.clicked.connect(self.reject); s.clicked.connect(self.accept)
#         btns.addStretch(); btns.addWidget(c); btns.addWidget(s)
#         lay.addLayout(btns)
#
#
# class ContainersTab(QWidget):
#     def __init__(self):
#         super().__init__()
#         self.setStyleSheet(TABLE_STYLE)
#         lay = QVBoxLayout(self); lay.setContentsMargins(0,12,0,0); lay.setSpacing(14)
#         hdr, _ = _header_bar(
#             "📦  Container Stock",
#             "Track trays, buckets, pots and other containers",
#             "＋  Add Container", self.add_container
#         )
#         lay.addLayout(hdr)
#         self.filter_bar = FilterBar(
#             columns=["Name"],
#             dropdown_label="Type",
#             dropdown_items=["Tray","Bucket","Pot","Box","Basket","Bag","Other"],
#             auto_refresh_sec=5,
#         )
#         self.filter_bar.filter_changed.connect(lambda s,c,d: self.load_data())
#         self.filter_bar.refresh_requested.connect(self.load_data)
#         lay.addWidget(self.filter_bar)
#
#         self.table = QTableWidget()
#         self.table.setColumnCount(7)
#         self.table.setHorizontalHeaderLabels(["ID","Name","Type","Capacity","Stock","Cost/Unit","Actions"])
#         hh = self.table.horizontalHeader()
#         for col,mode,w in [
#             (0,QHeaderView.ResizeMode.Fixed,50),
#             (1,QHeaderView.ResizeMode.Stretch,0),
#             (2,QHeaderView.ResizeMode.Fixed,90),
#             (3,QHeaderView.ResizeMode.Fixed,90),
#             (4,QHeaderView.ResizeMode.Fixed,80),
#             (5,QHeaderView.ResizeMode.Fixed,90),
#             (6,QHeaderView.ResizeMode.Fixed,210),
#         ]:
#             hh.setSectionResizeMode(col,mode)
#             if w: self.table.setColumnWidth(col,w)
#         self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
#         self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
#         self.table.verticalHeader().setVisible(False)
#         self.table.setAlternatingRowColors(True)
#         self.table.setStyleSheet(TABLE_STYLE+"QTableWidget{alternate-background-color:#F5FAF3;}")
#         lay.addWidget(self.table)
#
#         # ── Real-time updates ────────────────────────────────────────────────
#         db_signals.containers_changed.connect(self._on_db_change)
#         self.load_data()
#
#     def _ci(self, text):
#         it = QTableWidgetItem(str(text)); it.setTextAlignment(Qt.AlignmentFlag.AlignCenter); return it
#
#     def load_data(self):
#         try:
#             from services.user_service import ContainerService
#             all_conts = ContainerService.get_all()
#             q        = self.filter_bar.get_search()
#             col      = self.filter_bar.get_column()
#             dropdown = self.filter_bar.get_dropdown()
#             def cm(co):
#                 if dropdown and co.container_type != dropdown: return False
#                 if q:
#                     ql = q.lower()
#                     return ql in co.name.lower()
#                 return True
#             conts = [co for co in all_conts if cm(co)]
#             self.filter_bar.set_count(len(conts), len(all_conts))
#             self.table.setRowCount(0); self.table.setRowCount(len(conts))
#             TYPE_COLORS = {"Tray":"#2980B9","Bucket":"#8E44AD","Pot":"#27AE60",
#                            "Box":"#E67E22","Basket":"#16A085","Other":"#7F8C8D"}
#             for row, c in enumerate(conts):
#                 self.table.setRowHeight(row,52)
#                 self.table.setItem(row,0,self._ci(str(c.id or "")))
#                 ni = QTableWidgetItem(str(c.name)); ni.setFont(QFont("Segoe UI",13,QFont.Weight.Medium))
#                 self.table.setItem(row,1,ni)
#                 ti = self._ci(c.container_type)
#                 ti.setForeground(QColor(TYPE_COLORS.get(c.container_type,"#555")))
#                 f=ti.font(); f.setBold(True); ti.setFont(f)
#                 self.table.setItem(row,2,ti)
#                 self.table.setItem(row,3,self._ci(str(c.capacity)))
#                 si = self._ci(str(c.stock_qty))
#                 if c.stock_qty == 0: si.setForeground(QColor("#C0392B")); f=si.font(); f.setBold(True); si.setFont(f)
#                 self.table.setItem(row,4,si)
#                 self.table.setItem(row,5,self._ci(f"₹{float(c.unit_cost):.0f}"))
#
#                 bw = QWidget(); bw.setStyleSheet("background:transparent;")
#                 bl = QHBoxLayout(bw); bl.setContentsMargins(6,5,6,5); bl.setSpacing(6)
#                 bl.setAlignment(Qt.AlignmentFlag.AlignVCenter|Qt.AlignmentFlag.AlignLeft)
#                 add_b = _btn("+  Add",  "#1D6A38","#27AE60",w=68)
#                 rem_b = _btn("−  Use",  "#7D6608","#B7950B",w=68)
#                 edit_b= _btn("Edit",    "#2E7D32","#43A047",w=58)
#                 del_b = _btn("Delete",  "#C62828","#EF5350",w=65)
#                 add_b.clicked.connect(lambda _,co=c: self.adj_stock(co, add=True))
#                 rem_b.clicked.connect(lambda _,co=c: self.adj_stock(co, add=False))
#                 edit_b.clicked.connect(lambda _,co=c: self.edit_cont(co))
#                 del_b.clicked.connect(lambda _,cid=c.id: self.del_cont(cid))
#                 bl.addWidget(add_b); bl.addWidget(rem_b); bl.addWidget(edit_b); bl.addWidget(del_b)
#                 self.table.setCellWidget(row,6,bw)
#         except Exception as e:
#             self.table.setRowCount(1)
#             err=QTableWidgetItem(f"⚠  {e}"); err.setForeground(QColor("#C0392B"))
#             self.table.setItem(0,0,err)
#
#     def adj_stock(self, cont, add: bool):
#         action = "Add" if add else "Use/Remove"
#         from PyQt6.QtWidgets import QInputDialog
#         qty, ok = QInputDialog.getInt(self, f"{action} Stock",
#                                       f"How many {cont.container_type}s to {action.lower()}?",
#                                       1, 1, 99999)
#         if ok:
#             try:
#                 from services.user_service import ContainerService
#                 if add: ContainerService.add_stock(cont.id, qty)
#                 else:   ContainerService.remove_stock(cont.id, qty)
#                 self.load_data()
#             except Exception as e: QMessageBox.critical(self,"Error",str(e))
#
#     def add_container(self):
#         dlg = ContainerDialog(parent=self)
#         if dlg.exec() == QDialog.DialogCode.Accepted:
#             try:
#                 from services.user_service import ContainerService
#                 from models.user_model import Container
#                 co = Container(name=dlg.name_edit.text().strip(),
#                                container_type=dlg.type_combo.currentText(),
#                                capacity=dlg.cap_spin.value(),
#                                stock_qty=dlg.stock_spin.value(),
#                                unit_cost=dlg.cost_spin.value(),
#                                notes=dlg.notes_edit.text().strip())
#                 if not co.name: QMessageBox.warning(self,"Validation","Name required."); return
#                 ContainerService.save(co); self.load_data()
#             except Exception as e: QMessageBox.critical(self,"Error",str(e))
#
#     def edit_cont(self, cont):
#         dlg = ContainerDialog(cont=cont, parent=self)
#         if dlg.exec() == QDialog.DialogCode.Accepted:
#             try:
#                 from services.user_service import ContainerService
#                 cont.name=dlg.name_edit.text().strip(); cont.container_type=dlg.type_combo.currentText()
#                 cont.capacity=dlg.cap_spin.value(); cont.stock_qty=dlg.stock_spin.value()
#                 cont.unit_cost=dlg.cost_spin.value(); cont.notes=dlg.notes_edit.text().strip()
#                 ContainerService.save(cont); self.load_data()
#             except Exception as e: QMessageBox.critical(self,"Error",str(e))
#
#     def del_cont(self, cid):
#         if QMessageBox.question(self,"Confirm","Delete this container?",
#                 QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
#             try:
#                 from services.user_service import ContainerService
#                 ContainerService.delete(cid); self.load_data()
#             except Exception as e: QMessageBox.critical(self,"Error",str(e))
#
#     def _on_db_change(self, payload: str = ""):
#         """Called instantly when any table changes on any connected machine."""
#         self.load_data()
#
#
# ─────────────────────────────────────────────────────────────────────────────
#  Main Inventory Page
# ─────────────────────────────────────────────────────────────────────────────
class InventoryPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("InventoryPage{background:#F4F8F1;}" + TABLE_STYLE)

        main = QVBoxLayout(self)
        main.setContentsMargins(32,28,32,28)
        main.setSpacing(16)

        # Page title
        title = QLabel("Inventory")
        title.setStyleSheet("font-size:28px;font-weight:bold;color:#1A3A1A;")
        sub = QLabel("Manage plants, seeds and containers — all in one place.")
        sub.setStyleSheet("font-size:13px;color:#7A9A7A;")
        main.addWidget(title)
        main.addWidget(sub)

        # Tabs
        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.addTab(PlantsTab(),     "🪴   Plants")
        # tabs.addTab(SeedsTab(),      "🌱   Seeds")
        # tabs.addTab(ContainersTab(), "📦   Containers")
        main.addWidget(tabs)



