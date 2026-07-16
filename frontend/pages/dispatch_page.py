from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QDialog, QFormLayout, QComboBox, QTextEdit, QMessageBox,
    QHeaderView, QSizePolicy, QFrame, QLineEdit, QCheckBox, QGroupBox
)
from backend.realtime import db_signals
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QColor, QFont
from datetime import datetime
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
QTableWidget::item:hover    { background: #EEF8EE; }
QHeaderView::section {
    background: #EAF3E4; color: #2D5A2D; font-weight: bold; font-size: 13px;
    border: none; border-bottom: 2px solid #C8DFC0; padding: 12px 14px;
}
"""

DIALOG_STYLE = """
QDialog { background: #F7FAF5; }
QGroupBox {
    border: 1.5px solid #C8DFC0; border-radius: 8px;
    margin-top: 10px; font-weight: bold; color: #2D4A2D; font-size: 13px;
    padding: 8px;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
QLabel { font-size: 13px; color: #2D4A2D; }
QLineEdit, QComboBox, QTextEdit {
    border: 1.5px solid #C8DFC0; border-radius: 6px;
    padding: 8px 12px; font-size: 13px; background: white; color: #1A3A1A;
}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus { border: 1.5px solid #4A7C4A; }
QCheckBox { font-size: 13px; color: #2D4A2D; }
QCheckBox::indicator { width: 18px; height: 18px; border: 2px solid #4A7C4A; border-radius: 4px; }
QCheckBox::indicator:checked { background: #4A7C4A; }
"""

DELIVERY_COLORS = {
    "Pending":          "#E67E22",
    "Out for Delivery": "#2980B9",
    "Delivered":        "#27AE60",
    "Failed":           "#C0392B",
}

FAILURE_REASONS = [
    "Customer not available",
    "Wrong address",
    "Customer refused delivery",
    "Plant damaged in transit",
    "Vehicle breakdown",
    "Weather conditions",
    "Other",
]


class UpdateDeliveryDialog(QDialog):
    def __init__(self, order, parent=None):
        super().__init__(parent)
        self.order = order
        self.setWindowTitle(f"Update Delivery — Order ORD-{order.id:05d}")
        self.setMinimumWidth(560)
        self.setStyleSheet(DIALOG_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        # ── Header ──────────────────────────────────────────────────────────
        title = QLabel(f"ORD-{order.id:05d}  ·  {order.customer_name}")
        title.setStyleSheet("font-size:18px;font-weight:bold;color:#1E3A1E;")
        layout.addWidget(title)

        # ── Items summary ────────────────────────────────────────────────────
        if order.items:
            items_box = QFrame()
            items_box.setStyleSheet("background:#EAF3E4;border-radius:8px;")
            il = QVBoxLayout(items_box)
            il.setContentsMargins(12, 8, 12, 8); il.setSpacing(3)
            for item in order.items:
                r = QLabel(f"• {item.plant_name}  ×  {item.quantity}  —  ₹{item.subtotal:.0f}")
                r.setStyleSheet("font-size:12px;color:#2D5A2D;")
                il.addWidget(r)
            layout.addWidget(items_box)

        # ── Delivery Status ──────────────────────────────────────────────────
        status_group = QGroupBox("📦  Delivery Status")
        sg = QFormLayout(status_group)
        sg.setSpacing(10)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["Pending", "Out for Delivery", "Delivered", "Failed"])
        self.status_combo.setCurrentText(order.delivery_status or "Pending")
        self.status_combo.currentTextChanged.connect(self._on_status_change)

        self.failure_label = QLabel("Failure Reason *")
        self.failure_combo = QComboBox()
        self.failure_combo.addItems(FAILURE_REASONS)
        if order.failure_reason:
            idx = self.failure_combo.findText(order.failure_reason)
            if idx >= 0:
                self.failure_combo.setCurrentIndex(idx)

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Any additional delivery notes...")
        self.notes_edit.setFixedHeight(70)
        self.notes_edit.setPlainText(order.delivery_notes or "")

        sg.addRow("Status *", self.status_combo)
        sg.addRow(self.failure_label, self.failure_combo)
        sg.addRow("Notes", self.notes_edit)
        layout.addWidget(status_group)

        # ── Staff Details ────────────────────────────────────────────────────
        staff_group = QGroupBox("👷  Fulfilment Staff")
        stg = QFormLayout(staff_group)
        stg.setSpacing(10)

        self.packed_by_edit = QLineEdit()
        self.packed_by_edit.setPlaceholderText("Name of person who packed the order")
        self.packed_by_edit.setFixedHeight(40)
        self.packed_by_edit.setText(getattr(order, 'packed_by', '') or '')

        self.dispatched_by_edit = QLineEdit()
        self.dispatched_by_edit.setPlaceholderText("Name of driver / dispatch person")
        self.dispatched_by_edit.setFixedHeight(40)
        self.dispatched_by_edit.setText(getattr(order, 'dispatched_by', '') or '')

        self.received_by_edit = QLineEdit()
        self.received_by_edit.setPlaceholderText("Name of person who received at delivery")
        self.received_by_edit.setFixedHeight(40)
        self.received_by_edit.setText(getattr(order, 'received_by', '') or '')

        stg.addRow("📦 Packed By", self.packed_by_edit)
        stg.addRow("🚚 Dispatched By", self.dispatched_by_edit)
        stg.addRow("✅ Received By", self.received_by_edit)
        layout.addWidget(staff_group)

        # ── Buttons ──────────────────────────────────────────────────────────
        btns = QHBoxLayout(); btns.setSpacing(10)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(42)
        cancel_btn.setStyleSheet(
            "QPushButton { background:#E8EDE8;color:#2D4A2D;border:none;border-radius:8px;padding:0 24px;font-size:14px; }"
            "QPushButton:hover { background:#D0DAD0; }"
        )
        save_btn = QPushButton("💾  Save & Send")
        save_btn.setFixedHeight(42)
        save_btn.setStyleSheet(
            "QPushButton { background:#1E5C1E;color:white;border:none;border-radius:8px;padding:0 28px;font-size:14px;font-weight:bold; }"
            "QPushButton:hover { background:#2E7D2E; }"
            "QPushButton:pressed { background:#144014; }"
        )
        cancel_btn.clicked.connect(self.reject)
        save_btn.clicked.connect(self.accept)
        btns.addStretch()
        btns.addWidget(cancel_btn)
        btns.addWidget(save_btn)
        layout.addLayout(btns)

        self._on_status_change(self.status_combo.currentText())

    def _on_status_change(self, status):
        show_failure = (status == "Failed")
        self.failure_combo.setVisible(show_failure)
        self.failure_label.setVisible(show_failure)
        # Auto-enable received_by only for Delivered
        self.received_by_edit.setEnabled(status == "Delivered")
        if status != "Delivered":
            self.received_by_edit.setPlaceholderText("Available only when status = Delivered")
        else:
            self.received_by_edit.setPlaceholderText("Name of person who received at delivery")

    def get_values(self) -> dict:
        return {
            "delivery_status": self.status_combo.currentText(),
            "failure_reason":  self.failure_combo.currentText()
                               if self.status_combo.currentText() == "Failed" else "",
            "delivery_notes":  self.notes_edit.toPlainText().strip(),
            "packed_by":       self.packed_by_edit.text().strip(),
            "dispatched_by":   self.dispatched_by_edit.text().strip(),
            "received_by":     self.received_by_edit.text().strip(),
        }


# ─────────────────────────────────────────────────────────────────────────────
class DispatchPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(TABLE_STYLE)

        main = QVBoxLayout(self)
        main.setContentsMargins(32, 28, 32, 28)
        main.setSpacing(18)

        # ── Header ──────────────────────────────────────────────────────────
        header = QHBoxLayout()
        title_col = QVBoxLayout()
        title = QLabel("Dispatch Board")
        title.setStyleSheet("font-size:28px;font-weight:bold;color:#1A3A1A;")
        sub = QLabel("Update delivery status · Fill staff names · Send WhatsApp invoice")
        sub.setStyleSheet("font-size:13px;color:#7A9A7A;")
        title_col.addWidget(title)
        title_col.addWidget(sub)
        header.addLayout(title_col)
        main.addLayout(header)

        self.filter_bar = FilterBar(
            columns=["Order #","Customer","Packed By","Dispatched By"],
            dropdown_label="Delivery",
            dropdown_items=["Pending","Out for Delivery","Delivered","Failed"],
            auto_refresh_sec=5,
        )
        self.filter_bar.filter_changed.connect(self._on_filter)
        self.filter_bar.refresh_requested.connect(self.load_data)
        main.addWidget(self.filter_bar)

        # ── Badge row ────────────────────────────────────────────────────────
        self.badge_row = QHBoxLayout(); self.badge_row.setSpacing(12)
        self._badges = {}
        for key, label, color in [
            ("Pending",          "⏳ Pending",          "#E67E22"),
            ("Out for Delivery", "🚚 Out for Delivery",  "#2980B9"),
            ("Delivered",        "✅ Delivered",         "#27AE60"),
            ("Failed",           "❌ Failed",            "#C0392B"),
        ]:
            badge = QLabel(f"  {label}: 0  ")
            badge.setStyleSheet(f"background:{color};color:white;border-radius:10px;"
                                f"font-size:12px;font-weight:bold;padding:5px 14px;")
            self.badge_row.addWidget(badge)
            self._badges[key] = badge
        self.badge_row.addStretch()
        main.addLayout(self.badge_row)

        # ── Table ────────────────────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Order #", "Customer", "Items", "Order Status",
            "Delivery", "Packed By", "Dispatched By", "Action"
        ])
        self._column_min_widths = [100, 220, 70, 130, 150, 190, 190, 170]
        configure_scrollable_table(self.table, self._column_min_widths)

        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(
            TABLE_STYLE + "QTableWidget{alternate-background-color:#F5FAF3;}" + TABLE_SCROLLBAR_STYLE
        )
        main.addWidget(self.table)

        # ── Real-time DB updates (fires within 1 sec of any DB change) ────
        db_signals.orders_changed.connect(self._on_db_change)

        self.load_data()

    def _center(self, text):
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

    def _on_db_change(self, payload: str = ""):
        self.load_data()

    def _on_filter(self, search, col_idx, dropdown):
        self.load_data()

    def load_data(self):
        try:
            from services.user_service import OrderService
            all_orders = OrderService.get_all()
            all_active = [o for o in all_orders if o.status in ("Confirmed","Dispatched","Delivered")]
            query    = self.filter_bar.get_search()
            col      = self.filter_bar.get_column()
            dropdown = self.filter_bar.get_dropdown()

            def match(o):
                ds = getattr(o,'delivery_status','Pending') or 'Pending'
                if dropdown and ds != dropdown: return False
                if query:
                    ql = query.lower()
                    fields = [f"ord-{o.id:05d}", str(o.customer_name or ""),
                              str(getattr(o,'packed_by','') or ""),
                              str(getattr(o,'dispatched_by','') or "")]
                    if col == 0:
                        return any(ql in f.lower() for f in fields)
                    elif col <= len(fields):
                        return ql in fields[col-1].lower()
                return True

            active = [o for o in all_active if match(o)]
            self.filter_bar.set_count(len(active), len(all_active))

            counts = {"Pending": 0, "Out for Delivery": 0, "Delivered": 0, "Failed": 0}
            for o in active:
                ds = getattr(o, 'delivery_status', 'Pending') or 'Pending'
                if ds in counts:
                    counts[ds] += 1
            for key, badge in self._badges.items():
                prefix = badge.text().rsplit(":", 1)[0].strip()
                badge.setText(f"  {prefix}: {counts.get(key, 0)}  ")

            self.table.setRowCount(0)
            self.table.setRowCount(len(active))

            for row, o in enumerate(active):
                self.table.setRowHeight(row, 56)

                self.table.setItem(row, 0, self._center(f"ORD-{o.id:05d}"))

                name_item = QTableWidgetItem(str(o.customer_name or ""))
                name_item.setFont(QFont("Segoe UI", 13, QFont.Weight.Medium))
                self.table.setItem(row, 1, name_item)

                from services.user_service import OrderService as OS
                full_order = OS.get_by_id(o.id)
                self.table.setItem(row, 2, self._center(str(len(full_order.items) if full_order else 0)))

                ORDER_COLORS = {"Confirmed": "#2980B9", "Dispatched": "#8E44AD", "Delivered": "#27AE60"}
                os_item = self._center(o.status)
                os_item.setForeground(QColor(ORDER_COLORS.get(o.status, "#666")))
                f = os_item.font(); f.setBold(True); os_item.setFont(f)
                self.table.setItem(row, 3, os_item)

                ds = getattr(o, 'delivery_status', 'Pending') or 'Pending'
                ds_item = self._center(ds)
                ds_item.setForeground(QColor(DELIVERY_COLORS.get(ds, "#666")))
                f2 = ds_item.font(); f2.setBold(True); ds_item.setFont(f2)
                self.table.setItem(row, 4, ds_item)

                packed    = getattr(o, 'packed_by', '') or ''
                dispatched = getattr(o, 'dispatched_by', '') or ''
                self.table.setItem(row, 5, QTableWidgetItem(packed))
                self.table.setItem(row, 6, QTableWidgetItem(dispatched))

                # Action button
                btn_widget = QWidget()
                btn_widget.setStyleSheet("background:transparent;")
                bl = QHBoxLayout(btn_widget)
                bl.setContentsMargins(8, 6, 8, 6)
                bl.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

                if ds == "Delivered":
                    received = getattr(o, 'received_by', '') or ''
                    done_lbl = QLabel(f"✅  {received}" if received else "✅ Delivered")
                    done_lbl.setStyleSheet("color:#27AE60;font-weight:bold;font-size:13px;")
                    bl.addWidget(done_lbl)
                else:
                    upd_btn = QPushButton("Update & Send")
                    upd_btn.setFixedSize(QSize(138, 36))
                    upd_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    upd_btn.setStyleSheet(
                        "QPushButton{background:#1A5276;color:white;font-size:13px;"
                        "font-weight:bold;border:none;border-radius:6px;}"
                        "QPushButton:hover{background:#2471A3;}"
                        "QPushButton:pressed{background:#0E3460;}"
                    )
                    upd_btn.clicked.connect(lambda _, ord=o: self.update_delivery(ord))
                    bl.addWidget(upd_btn)

                self.table.setCellWidget(row, 7, btn_widget)

            fit_table_columns_to_contents(self.table, self._column_min_widths)

        except Exception as e:
            self.table.setRowCount(1)
            err = QTableWidgetItem(f"⚠  Error: {e}")
            err.setForeground(QColor("#C0392B"))
            self.table.setItem(0, 0, err)

    def update_delivery(self, order):
        try:
            from services.user_service import OrderService
            full_order = OrderService.get_by_id(order.id)
            if not full_order:
                return
            # Copy delivery fields into full_order
            for attr in ('delivery_status', 'delivery_notes', 'failure_reason',
                         'packed_by', 'dispatched_by', 'received_by'):
                setattr(full_order, attr, getattr(order, attr, '') or '')

            dlg = UpdateDeliveryDialog(full_order, parent=self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return

            vals = dlg.get_values()

            # Save to DB
            OrderService.update_delivery(
                order.id,
                vals["delivery_status"],
                vals["delivery_notes"],
                vals["failure_reason"],
                vals["packed_by"],
                vals["dispatched_by"],
                vals["received_by"],
            )

            # Auto-update order status when delivered
            if vals["delivery_status"] == "Delivered":
                OrderService.update_status(order.id, "Delivered")

            # Re-fetch updated order with all fields
            updated_order = OrderService.get_by_id(order.id)

            # Generate updated invoice PDF with staff names
            invoice_path = self._generate_invoice(updated_order)

            self.load_data()
            msg = f"✅ Delivery status updated to: {vals['delivery_status']}"
            if invoice_path:
                msg += f"\n📄 Invoice PDF saved to HindAgro_Invoices folder."
            QMessageBox.information(self, "Updated", msg)

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _generate_invoice(self, order) -> str:
        """Regenerate the invoice PDF with updated staff names."""
        try:
            import os
            from services.pdf_service import generate_customer_invoice
            save_dir = os.path.join(os.path.expanduser("~"), "Hind Agro Products_Invoices")
            os.makedirs(save_dir, exist_ok=True)
            path = os.path.join(save_dir, f"Invoice_ORD-{order.id:05d}.pdf")
            generate_customer_invoice(order, path)
            return path
        except Exception as e:
            print(f"[PDF] Error: {e}")
            return ""
