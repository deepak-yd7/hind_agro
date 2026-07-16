from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QDialog, QFormLayout, QComboBox, QTextEdit, QMessageBox,
    QHeaderView, QSpinBox, QDoubleSpinBox, QSizePolicy
)
from backend.realtime import db_signals
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QColor, QFont
from backend.database import get_table_columns
from frontend.filter_bar import FilterBar
from frontend.table_utils import (
    TABLE_SCROLLBAR_STYLE,
    configure_scrollable_table,
    fit_table_columns_to_contents,
)

TABLE_STYLE = """
QTableWidget {
    background: white; border-radius: 10px; border: 1px solid #D8E8D0;
    gridline-color: #EEF5EA; font-size: 14px; outline: none;
}
QTableWidget::item { padding: 0px 14px; color: #1A3A1A; border: none; }
QTableWidget::item:selected { background: #D6EDD6; color: #1A3A1A; }
QTableWidget::item:hover { background: #EEF8EE; }
QHeaderView::section {
    background: #EAF3E4; color: #2D5A2D; font-weight: bold; font-size: 13px;
    border: none; border-bottom: 2px solid #C8DFC0; padding: 12px 14px;
}
QComboBox {
    border: 1.5px solid #C8DFC0; border-radius: 6px; padding: 4px 10px;
    font-size: 12px; background: white; color: #1A3A1A;
}
QComboBox:focus { border: 1.5px solid #4A7C4A; }
QComboBox QAbstractItemView {
    background: white;
    color: #111111;
    selection-background-color: #D6EDD6;
    selection-color: #111111;
}
"""

DIALOG_STYLE = """
QDialog { background: #F7FAF5; }
QLabel { font-size: 13px; color: #2D4A2D; font-weight: 500; }
QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    border: 1.5px solid #C8DFC0; border-radius: 6px;
    padding: 7px 12px; font-size: 13px; background: white; color: #1A3A1A;
}
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1.5px solid #4A7C4A;
}
QComboBox QAbstractItemView {
    background: white;
    color: #111111;
    selection-background-color: #D6EDD6;
    selection-color: #111111;
}
"""

STATUS_COLORS = {
    "Pending":   "#E67E22",
    "Confirmed": "#2980B9",
    "Dispatched":"#8E44AD",
    "Delivered": "#27AE60",
    "Cancelled": "#95A5A6",
}


def _ordered_items_text(order) -> str:
    parts = []
    for item in order.items:
        label = str(item.plant_name or "").strip() or "Item"
        parts.append(f"{label} x{item.quantity}")
    return ", ".join(parts)


def _ordered_categories_text(order) -> str:
    categories = []
    seen = set()
    for item in order.items:
        category = str(getattr(item, "plant_category", "") or "").strip()
        if category and category not in seen:
            seen.add(category)
            categories.append(category)
    return ", ".join(categories) if categories else "-"


class OrderItemRow(QWidget):
    def __init__(self, lots, parent=None):
        super().__init__(parent)
        self.lots = lots
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(8)

        self.lot_combo = QComboBox()
        self.lot_combo.setStyleSheet(DIALOG_STYLE.split("QDialog")[1] if "QComboBox" in DIALOG_STYLE else "")
        for p in lots:
            category = f" | {p.category}" if getattr(p, "category", "") else ""
            self.lot_combo.addItem(f"{p.name}{category}  (Stock: {p.stock_qty})", userData=p)
        self.lot_combo.currentIndexChanged.connect(self._update_price)

        self.qty_spin = QSpinBox()
        self.qty_spin.setMinimum(1)
        self.qty_spin.setMaximum(9999)
        self.qty_spin.setFixedWidth(80)

        self.price_lbl = QLabel("₹ 0.00")
        self.price_lbl.setFixedWidth(90)
        self.price_lbl.setStyleSheet("color:#2D4A2D; font-weight:bold; font-size:13px;")

        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(QSize(32, 32))
        remove_btn.setStyleSheet(
            "QPushButton { background:#C62828; color:white; border:none; border-radius:6px; font-size:14px; font-weight:bold; }"
            "QPushButton:hover { background:#EF5350; }"
        )
        remove_btn.clicked.connect(lambda: self.setParent(None))

        layout.addWidget(self.lot_combo, 3)
        layout.addWidget(self.qty_spin, 1)
        layout.addWidget(self.price_lbl, 1)
        layout.addWidget(remove_btn)
        self._update_price()

    def _update_price(self):
        p = self.lot_combo.currentData()
        if p:
            self.price_lbl.setText(f"₹ {p.unit_price:.2f}")

    def get_item_data(self):
        p = self.lot_combo.currentData()
        return {"lot": p, "qty": self.qty_spin.value()}


class NewOrderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Order")
        self.setMinimumWidth(580)
        self.setStyleSheet(DIALOG_STYLE)

        self.item_rows = []
        self.lots = []
        self.customers = []

        try:
            from services.user_service import CustomerService, ProductionLotService # <--- IMPORT IT FROM HERE INSTEAD

            self.customers = CustomerService.get_all()
            self.lots = ProductionLotService.get_hardened_inventory()
        except Exception as e:
            print(f"Error loading order prerequisites: {e}")
            self.customers = []
            self.lots = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(0)

        title = QLabel("Place New Order")
        title.setStyleSheet("font-size:18px;font-weight:bold;color:#1E3A1E;margin-bottom:16px;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setContentsMargins(0, 0, 0, 16)

        self.cust_combo = QComboBox()
        for c in self.customers:
            self.cust_combo.addItem(c.name, userData=c)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["Pending", "Confirmed", "Dispatched", "Delivered", "Cancelled"])

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Optional order notes...")
        self.notes_edit.setFixedHeight(60)

        form.addRow("Customer *", self.cust_combo)
        form.addRow("Status",     self.status_combo)
        form.addRow("Notes",      self.notes_edit)
        layout.addLayout(form)

        items_label = QLabel("Order Items (From Hardening Stage)")
        items_label.setStyleSheet("font-weight:bold;color:#1E3A1E;font-size:14px;margin-bottom:8px;")
        layout.addWidget(items_label)

        col_header = QHBoxLayout()
        for txt, stretch in [("Plant Lot", 3), ("Qty", 1), ("Unit Price", 1), ("", 0)]:
            lbl = QLabel(txt)
            lbl.setStyleSheet("font-size:12px;color:#6B8F6B;font-weight:bold;")
            col_header.addWidget(lbl, stretch if stretch else 0)
            if stretch == 0:
                lbl.setFixedWidth(32)
        layout.addLayout(col_header)

        self.items_container = QVBoxLayout()
        self.items_container.setSpacing(6)
        layout.addLayout(self.items_container)

        add_item_btn = QPushButton("＋  Add Item")
        add_item_btn.setFixedHeight(34)
        add_item_btn.setStyleSheet(
            "QPushButton { background:#3A6B3A; color:white; border:none; border-radius:6px;"
            " padding:0 16px; font-size:13px; font-weight:bold; margin-top:8px; }"
            "QPushButton:hover { background:#4E8F4E; }"
        )
        add_item_btn.clicked.connect(self.add_item_row)
        layout.addWidget(add_item_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addSpacing(12)
        self.add_item_row()

        btns = QHBoxLayout(); btns.setSpacing(10)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(38)
        cancel_btn.setStyleSheet(
            "QPushButton { background:#E8EDE8; color:#2D4A2D; border:none; border-radius:7px; padding:0 20px; font-size:13px; }"
            "QPushButton:hover { background:#D0DAD0; }"
        )
        save_btn = QPushButton("Place Order")
        save_btn.setFixedHeight(38)
        save_btn.setStyleSheet(
            "QPushButton { background:#2D4A2D; color:white; border:none; border-radius:7px; padding:0 24px; font-size:13px; font-weight:bold; }"
            "QPushButton:hover { background:#3D6B3D; }"
            "QPushButton:pressed { background:#1E3A1E; }"
        )
        cancel_btn.clicked.connect(self.reject)
        save_btn.clicked.connect(self.accept)
        btns.addStretch(); btns.addWidget(cancel_btn); btns.addWidget(save_btn)
        layout.addLayout(btns)

    def add_item_row(self):
        if not self.lots:
            QMessageBox.warning(self, "No Inventory", "No plants available in hardening stage.")
            return
        row = OrderItemRow(self.lots, self)
        self.items_container.addWidget(row)
        self.item_rows.append(row)



class InvoicePricingDialog(QDialog):
    def __init__(self, order, default_discount_percent=0.0, parent=None):
        super().__init__(parent)
        self.order = order
        self.price_spins = {}
        self.setWindowTitle(f"Invoice Pricing - ORD-{order.id:05d}")
        self.setMinimumWidth(760)
        self.setStyleSheet(DIALOG_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        title = QLabel(f"Invoice Pricing - {order.customer_name}")
        title.setStyleSheet("font-size:18px;font-weight:bold;color:#1E3A1E;")
        layout.addWidget(title)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Item", "Qty", "Current Price", "Invoice Price", "Line Total"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(TABLE_STYLE + "QTableWidget{alternate-background-color:#F5FAF3;}")
        self.table.setRowCount(len(order.items))
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setColumnWidth(0, 260)
        self.table.setColumnWidth(1, 70)
        self.table.setColumnWidth(2, 120)
        self.table.setColumnWidth(3, 130)
        self.table.setColumnWidth(4, 120)

        for row, item in enumerate(order.items):
            self.table.setRowHeight(row, 44)
            self.table.setItem(row, 0, QTableWidgetItem(item.plant_name or "Item"))
            self.table.setItem(row, 1, self._center(str(item.quantity)))
            self.table.setItem(row, 2, self._center(f"Rs {float(item.unit_price):.2f}"))

            price_spin = QDoubleSpinBox()
            price_spin.setRange(0, 999999)
            price_spin.setDecimals(2)
            price_spin.setPrefix("Rs ")
            price_spin.setValue(float(item.unit_price or 0))
            price_spin.valueChanged.connect(self._price_changed)
            self.price_spins[item.id] = price_spin
            self.table.setCellWidget(row, 3, price_spin)
            self.table.setItem(row, 4, self._center("Rs 0.00"))

        layout.addWidget(self.table)

        form = QFormLayout()
        form.setSpacing(10)

        self.discount_percent_spin = QDoubleSpinBox()
        self.discount_percent_spin.setRange(0, 100)
        self.discount_percent_spin.setDecimals(2)
        self.discount_percent_spin.setSuffix(" %")
        self.discount_percent_spin.setValue(float(default_discount_percent or 0))
        self.discount_percent_spin.valueChanged.connect(self._discount_percent_changed)

        self.discount_amount_spin = QDoubleSpinBox()
        self.discount_amount_spin.setRange(0, 99999999)
        self.discount_amount_spin.setDecimals(2)
        self.discount_amount_spin.setPrefix("Rs ")
        self.discount_amount_spin.valueChanged.connect(self._recalculate)

        self.notes_edit = QTextEdit()
        self.notes_edit.setFixedHeight(55)
        self.notes_edit.setPlaceholderText("Optional note, e.g. Owner approved special customer price.")

        form.addRow("Discount", self.discount_percent_spin)
        form.addRow("Discount Amount", self.discount_amount_spin)
        form.addRow("Price Note", self.notes_edit)
        layout.addLayout(form)

        self.total_lbl = QLabel()
        self.total_lbl.setStyleSheet(
            "background:#EAF3E4;border-radius:8px;padding:10px 14px;"
            "font-size:14px;font-weight:bold;color:#1E3A1E;"
        )
        layout.addWidget(self.total_lbl)

        btns = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(38)
        cancel_btn.setStyleSheet(
            "QPushButton { background:#E8EDE8; color:#2D4A2D; border:none; border-radius:7px; padding:0 20px; font-size:13px; }"
            "QPushButton:hover { background:#D0DAD0; }"
        )
        save_btn = QPushButton("Generate Invoice")
        save_btn.setFixedHeight(38)
        save_btn.setStyleSheet(
            "QPushButton { background:#2D4A2D; color:white; border:none; border-radius:7px; padding:0 24px; font-size:13px; font-weight:bold; }"
            "QPushButton:hover { background:#3D6B3D; }"
        )
        cancel_btn.clicked.connect(self.reject)
        save_btn.clicked.connect(self.accept)
        btns.addStretch()
        btns.addWidget(cancel_btn)
        btns.addWidget(save_btn)
        layout.addLayout(btns)

        self._discount_percent_changed(self.discount_percent_spin.value())

    def _center(self, text):
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

    def _subtotal(self):
        total = 0.0
        for item in self.order.items:
            spin = self.price_spins.get(item.id)
            price = spin.value() if spin else float(item.unit_price or 0)
            total += price * int(item.quantity or 0)
        return total

    def _discount_percent_changed(self, percent):
        subtotal = self._subtotal()
        self.discount_amount_spin.blockSignals(True)
        self.discount_amount_spin.setValue(subtotal * float(percent or 0) / 100)
        self.discount_amount_spin.blockSignals(False)
        self._recalculate()

    def _price_changed(self):
        if self.discount_percent_spin.value() > 0:
            self._discount_percent_changed(self.discount_percent_spin.value())
        else:
            self._recalculate()

    def _recalculate(self):
        subtotal = self._subtotal()
        discount = min(self.discount_amount_spin.value(), subtotal)
        if discount != self.discount_amount_spin.value():
            self.discount_amount_spin.blockSignals(True)
            self.discount_amount_spin.setValue(discount)
            self.discount_amount_spin.blockSignals(False)

        for row, item in enumerate(self.order.items):
            spin = self.price_spins.get(item.id)
            price = spin.value() if spin else float(item.unit_price or 0)
            self.table.item(row, 4).setText(f"Rs {price * int(item.quantity or 0):.2f}")

        final_total = max(0, subtotal - discount)
        self.total_lbl.setText(
            f"Subtotal: Rs {subtotal:.2f}    Discount: Rs {discount:.2f}    Final Invoice: Rs {final_total:.2f}"
        )

    def get_values(self):
        return {
            "item_prices": {
                item_id: spin.value()
                for item_id, spin in self.price_spins.items()
                if item_id is not None
            },
            "discount_amount": self.discount_amount_spin.value(),
            "price_note": self.notes_edit.toPlainText().strip(),
        }


class OrdersPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(TABLE_STYLE)

        main = QVBoxLayout(self)
        main.setContentsMargins(32, 28, 32, 28)
        main.setSpacing(18)

        # â”€â”€ Header â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        header = QHBoxLayout()
        title = QLabel("Orders")
        title.setStyleSheet("font-size:28px;font-weight:bold;color:#1A3A1A;")
        header.addWidget(title)
        header.addStretch()

        add_btn = QPushButton("ï¼‹  New Order")
        add_btn.setFixedHeight(38)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet(
            "QPushButton { background:#2D4A2D; color:white; border:none; border-radius:8px;"
            " padding:0 22px; font-size:14px; font-weight:bold; }"
            "QPushButton:hover { background:#3D6B3D; }"
            "QPushButton:pressed { background:#1E3A1E; }"
        )
        add_btn.clicked.connect(self.new_order)
        header.addWidget(add_btn)
        main.addLayout(header)

        # â”€â”€ Filter Bar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self.filter_bar = FilterBar(
            columns=["Order #", "Customer", "Ordered Item", "Category", "Total"],
            dropdown_label="Status",
            dropdown_items=["", "Pending", "Confirmed", "Dispatched", "Delivered", "Cancelled"]
        )

        self.filter_bar.filter_changed.connect(self._on_filter)
        self.filter_bar.refresh_requested.connect(self.load_data)

        main.addWidget(self.filter_bar)

        # â”€â”€ Table â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ["Order #", "Customer", "Ordered Item", "Category", "Date", "Status", "Total (Rs)", "Actions"]
        )
        self._column_min_widths = [90, 220, 300, 190, 120, 130, 130, 280]
        configure_scrollable_table(self.table, self._column_min_widths)

        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(
            TABLE_STYLE + "QTableWidget { alternate-background-color: #F5FAF3; }" + TABLE_SCROLLBAR_STYLE
        )
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main.addWidget(self.table)
        # â”€â”€ Real-time DB updates (fires within 1 sec of any DB change) â”€â”€â”€â”€
        db_signals.orders_changed.connect(self._on_db_change)
        db_signals.customers_changed.connect(self._on_db_change)

        self.load_data()

    def _center_item(self, text):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

    def _on_db_change(self, payload: str = ""):
        """Called instantly when DB changes on any connected machine."""
        self.load_data()

    def _on_filter(self, search, col_idx, dropdown):
        self.load_data()

    def load_data(self):
        try:
            from services.user_service import OrderService
            all_orders = OrderService.get_all()
            query    = self.filter_bar.get_search()
            col      = self.filter_bar.get_column()
            dropdown = self.filter_bar.get_dropdown()

            def match(o):
                if dropdown and o.status != dropdown: return False
                if query:
                    ql = query.lower()
                    fields = [
                        f"ord-{o.id:05d}",
                        str(o.customer_name or ""),
                        _ordered_items_text(o),
                        _ordered_categories_text(o),
                        str(o.total_amount or ""),
                    ]
                    if col == 0:
                        return any(ql in f.lower() for f in fields)
                    elif col <= len(fields):
                        return ql in fields[col-1].lower()
                return True

            orders = [o for o in all_orders if match(o)]
            self.filter_bar.set_count(len(orders), len(all_orders))

            self.table.setRowCount(0)
            self.table.setRowCount(len(orders))

            for row, o in enumerate(orders):
                self.table.setRowHeight(row, 52)

                self.table.setItem(row, 0, self._center_item(str(o.id or "")))

                name_item = QTableWidgetItem(str(o.customer_name or ""))
                name_item.setFont(QFont("Segoe UI", 13, QFont.Weight.Medium))
                self.table.setItem(row, 1, name_item)

                self.table.setItem(row, 2, QTableWidgetItem(_ordered_items_text(o)))
                self.table.setItem(row, 3, self._center_item(_ordered_categories_text(o)))

                date_str = o.order_date.strftime("%d %b %Y") if o.order_date else ""
                self.table.setItem(row, 4, self._center_item(date_str))

                status_item = self._center_item(o.status or "")
                color = STATUS_COLORS.get(o.status, "#666")
                status_item.setForeground(QColor(color))
                f = status_item.font(); f.setBold(True); status_item.setFont(f)
                self.table.setItem(row, 5, status_item)


                # â”€â”€ Action buttons â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                self.table.setItem(row, 6, self._center_item(f"Rs {float(o.total_amount):.2f}"))

                btn_widget = QWidget()
                btn_widget.setStyleSheet("background: transparent;")
                btn_layout = QHBoxLayout(btn_widget)
                btn_layout.setContentsMargins(8, 6, 8, 6)
                btn_layout.setSpacing(8)
                btn_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

                # Status change combo
                status_combo = QComboBox()
                status_combo.addItems(["Pending", "Confirmed", "Dispatched", "Delivered", "Cancelled"])
                status_combo.setCurrentText(o.status)
                status_combo.setFixedSize(QSize(130, 34))
                status_combo.setStyleSheet(
                    "QComboBox { border:1.5px solid #C8DFC0; border-radius:6px; padding:4px 10px;"
                    " font-size:12px; background:white; color:#1A3A1A; }"
                    "QComboBox:hover { border:1.5px solid #4A7C4A; }"
                    "QComboBox QAbstractItemView { background:white; color:#111111;"
                    " selection-background-color:#D6EDD6; selection-color:#111111; }"
                )
                status_combo.currentTextChanged.connect(lambda s, oid=o.id: self.update_status(oid, s))

                inv_btn = QPushButton("Invoice")
                inv_btn.setFixedSize(QSize(90, 34))
                inv_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                inv_btn.setStyleSheet(
                    "QPushButton { background-color:#1A5276; color:white; font-size:13px;"
                    " font-weight:bold; border:none; border-radius:6px; }"
                    "QPushButton:hover { background-color:#2471A3; }"
                    "QPushButton:pressed { background-color:#0E3460; }"
                )
                inv_btn.clicked.connect(lambda _, oid=o.id: self.create_invoice(oid))

                btn_layout.addWidget(status_combo)
                btn_layout.addWidget(inv_btn)
                self.table.setCellWidget(row, 7, btn_widget)

            fit_table_columns_to_contents(self.table, self._column_min_widths)

        except Exception as e:
            self.table.setRowCount(1)
            self.table.setRowHeight(0, 52)
            err = QTableWidgetItem(f"âš   DB not connected: {e}")
            err.setForeground(QColor("#C0392B"))
            self.table.setItem(0, 0, err)

    def new_order(self):
        dlg = NewOrderDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                from services.user_service import OrderService
                from models.user_model import Order, OrderItem

                cust = dlg.cust_combo.currentData()
                if not cust: return

                items = []
                for i in range(dlg.items_container.count()):
                    w = dlg.items_container.itemAt(i).widget()
                    if w and hasattr(w, 'get_item_data'):
                        d = w.get_item_data()
                        lot = d["lot"] # The Lot object containing the hardening price
                        if lot:
                            items.append(OrderItem(
                                production_lot_id=lot.id,
                                plant_name=lot.name,
                                quantity=d["qty"],
                                unit_price=float(lot.unit_price), # Explicitly cast to float
                                plant_category=lot.category,
                            ))

                if not items: return

                order = Order(
                    customer_id=cust.id,
                    status=dlg.status_combo.currentText(),
                    notes=dlg.notes_edit.toPlainText(),
                    items=items,
                )
                OrderService.save(order)
                self.load_data()
                QMessageBox.information(self, "Success", "Order placed successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def update_status(self, order_id, status):
        try:
            from services.user_service import OrderService
            OrderService.update_status(order_id, status)
        except:
            pass

    def create_invoice(self, order_id):
        try:
            import os, subprocess, sys
            from services.user_service import CustomerService, InvoiceService, OrderService
            from services.pdf_service import generate_customer_invoice, generate_dispatch_slip

            # Fetch full order with items populated
            order = OrderService.get_by_id(order_id)
            if not order:
                QMessageBox.warning(self, "Error", f"Order #{order_id} not found.")
                return
            if not order.items:
                QMessageBox.warning(self, "No Items", "This order has no items. Cannot generate invoice.")
                return

            default_discount = 0.0
            for customer in CustomerService.get_all():
                if customer.id == order.customer_id:
                    default_discount = float(getattr(customer, "discount_percent", 0) or 0)
                    break

            pricing_dlg = InvoicePricingDialog(order, default_discount, parent=self)
            if pricing_dlg.exec() != QDialog.DialogCode.Accepted:
                return
            pricing = pricing_dlg.get_values()

            OrderService.update_invoice_pricing(order_id, pricing["item_prices"])
            InvoiceService.create_for_order(
                order_id,
                discount_amount=pricing["discount_amount"],
                price_override_notes=pricing["price_note"],
            )

            # Re-fetch after owner price rewrite so PDFs and invoice list match.
            order = OrderService.get_by_id(order_id)
            order.invoice_discount_amount = pricing["discount_amount"]
            order.price_override_notes = pricing["price_note"]

            # Save to ~/Hind Agro Products_Invoices/
            save_dir = os.path.join(os.path.expanduser("~"), "Hind Agro Products_Invoices")
            os.makedirs(save_dir, exist_ok=True)

            invoice_path  = os.path.join(save_dir, f"Invoice_ORD-{order_id:05d}.pdf")
            dispatch_path = os.path.join(save_dir, f"DispatchSlip_ORD-{order_id:05d}.pdf")

            generate_customer_invoice(order, invoice_path)
            generate_dispatch_slip(order, dispatch_path)

            # Open both PDFs with the system default viewer
            for path in [invoice_path, dispatch_path]:
                if sys.platform.startswith("win"):
                    os.startfile(path)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", path])
                else:
                    subprocess.Popen(["xdg-open", path])

            QMessageBox.information(
                self, "PDFs Generated",
                f"Two PDFs saved to:\n{save_dir}\n\n"
                f"  Invoice_ORD-{order_id:05d}.pdf\n"
                f"  DispatchSlip_ORD-{order_id:05d}.pdf\n\n"
                "Both files have been opened."
            )
        except Exception as e:
            QMessageBox.critical(self, "PDF Error", str(e))
