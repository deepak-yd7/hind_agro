from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QMessageBox, QSizePolicy
)
from backend.realtime import db_signals
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QFont
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


class InvoicesPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(TABLE_STYLE)

        main = QVBoxLayout(self)
        main.setContentsMargins(32, 28, 32, 28)
        main.setSpacing(18)

        # ── Header ──────────────────────────────────────────────
        hdr = QHBoxLayout()
        title = QLabel("Invoices")
        title.setStyleSheet("font-size:28px;font-weight:bold;color:#1A3A1A;")
        sub = QLabel("View, filter and manage all invoices.")
        sub.setStyleSheet("font-size:13px;color:#7A9A7A;")
        tc = QVBoxLayout(); tc.addWidget(title); tc.addWidget(sub)
        hdr.addLayout(tc)
        main.addLayout(hdr)

        # ── Filter bar ───────────────────────────────────────────
        self.filter_bar = FilterBar(
            columns=["Invoice #", "Order #", "Customer", "Amount"],
            dropdown_label="Status",
            dropdown_items=["Paid", "Unpaid", "Overdue"],
            auto_refresh_sec=5,
        )
        self.filter_bar.filter_changed.connect(self._on_filter)
        self.filter_bar.refresh_requested.connect(self.load_data)
        main.addWidget(self.filter_bar)

        # ── Table ────────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self._column_min_widths = [110, 100, 240, 120, 120, 110, 130, 120, 140]
        self.table.setHorizontalHeaderLabels([
            "Invoice #", "Order #", "Customer", "Date", "Due Date",
            "Discount", "Amount (Rs)", "Status", "Action"
        ])
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


        # ── Real-time DB updates (fires within 1 sec of any DB change) ────
        db_signals.invoices_changed.connect(self._on_db_change)
        db_signals.orders_changed.connect(self._on_db_change)

        self.load_data()

    def _center_item(self, text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

    def _invoice_number(self, inv) -> str:
        return f"INV-{int(inv.id):05d}" if inv.id else ""

    def _order_number(self, inv) -> str:
        return f"ORD-{int(inv.order_id):05d}" if inv.order_id else ""

    def _date_only(self, value):
        if value is None:
            return None
        if hasattr(value, "date"):
            return value.date()
        return value

    def _on_db_change(self, payload: str = ""):
        """Called instantly when DB changes on any connected machine."""
        self.load_data()

    def _on_filter(self, search, col_idx, dropdown):
        self.load_data()

    def load_data(self):
        try:
            from services.user_service import InvoiceService
            from datetime import date

            all_invoices = InvoiceService.get_all()
            query    = self.filter_bar.get_search()
            col      = self.filter_bar.get_column()
            dropdown = self.filter_bar.get_dropdown()

            def match(inv):
                if dropdown == "Paid"   and not inv.paid: return False
                if dropdown == "Unpaid" and inv.paid:     return False
                if dropdown == "Overdue":
                    if inv.paid: return False
                    due_date = self._date_only(inv.due_date)
                    if due_date and due_date < date.today(): pass
                    else: return False
                if query:
                    ql = query.lower()
                    fields = [self._invoice_number(inv), self._order_number(inv),
                              str(inv.customer_name or ""), str(inv.total_amount or "")]
                    if col == 0:
                        return any(ql in f.lower() for f in fields)
                    elif col <= len(fields):
                        return ql in fields[col-1].lower()
                return True

            invoices = [i for i in all_invoices if match(i)]
            self.filter_bar.set_count(len(invoices), len(all_invoices))

            self.table.clearSpans()
            self.table.setRowCount(0)
            self.table.setRowCount(len(invoices))

            for row, inv in enumerate(invoices):
                self.table.setRowHeight(row, 52)

                self.table.setItem(row, 0, self._center_item(self._invoice_number(inv)))
                self.table.setItem(row, 1, self._center_item(self._order_number(inv)))

                name_item = QTableWidgetItem(str(inv.customer_name or ""))
                name_item.setFont(QFont("Segoe UI", 13, QFont.Weight.Medium))
                self.table.setItem(row, 2, name_item)

                date_str = inv.invoice_date.strftime("%d %b %Y") if inv.invoice_date else ""
                due_str  = inv.due_date.strftime("%d %b %Y")     if inv.due_date      else ""
                self.table.setItem(row, 3, self._center_item(date_str))

                due_item = self._center_item(due_str)
                # Highlight overdue
                due_date = self._date_only(inv.due_date)
                if due_date and not inv.paid:
                    if due_date < date.today():
                        due_item.setForeground(QColor("#C0392B"))
                        f = due_item.font(); f.setBold(True); due_item.setFont(f)
                self.table.setItem(row, 4, due_item)

                amt_item = self._center_item(f"₹ {float(inv.total_amount):.2f}")
                amt_item.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
                self.table.setItem(row, 5, self._center_item(
                    f"Rs {float(getattr(inv, 'discount_amount', 0) or 0):.2f}"
                ))
                self.table.setItem(row, 6, amt_item)

                if inv.paid:
                    paid_item = self._center_item("✅  Paid")
                    paid_item.setForeground(QColor("#27AE60"))
                    f = paid_item.font(); f.setBold(True); paid_item.setFont(f)
                else:
                    paid_item = self._center_item("⏳  Pending")
                    paid_item.setForeground(QColor("#E67E22"))
                    f = paid_item.font(); f.setBold(True); paid_item.setFont(f)
                self.table.setItem(row, 7, paid_item)

                # ── Action button ───────────────────────────────
                btn_widget = QWidget()
                btn_widget.setStyleSheet("background: transparent;")
                btn_layout = QHBoxLayout(btn_widget)
                btn_layout.setContentsMargins(8, 6, 8, 6)
                btn_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

                if not inv.paid:
                    mark_btn = QPushButton("Mark Paid")
                    mark_btn.setFixedSize(QSize(110, 34))
                    mark_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    mark_btn.setStyleSheet(
                        "QPushButton { background-color:#1D6A38; color:white; font-size:13px;"
                        " font-weight:bold; border:none; border-radius:6px; }"
                        "QPushButton:hover { background-color:#27AE60; }"
                        "QPushButton:pressed { background-color:#145A32; }"
                    )
                    mark_btn.clicked.connect(lambda _, iid=inv.id: self.mark_paid(iid))
                    btn_layout.addWidget(mark_btn)
                else:
                    done_lbl = QLabel("—")
                    done_lbl.setStyleSheet("color:#95A5A6; font-size:13px;")
                    done_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    btn_layout.addWidget(done_lbl)

                self.table.setCellWidget(row, 8, btn_widget)

            fit_table_columns_to_contents(self.table, self._column_min_widths)

        except Exception as e:
            self.table.clearSpans()
            self.table.setRowCount(1)
            self.table.setRowHeight(0, 52)
            self.table.setSpan(0, 0, 1, self.table.columnCount())
            err = QTableWidgetItem(f"⚠  Could not load invoices: {e}")
            err.setForeground(QColor("#C0392B"))
            self.table.setItem(0, 0, err)

    def mark_paid(self, invoice_id: int):
        reply = QMessageBox.question(
            self, "Confirm Payment",
            f"Mark Invoice #{invoice_id} as paid?\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                from services.user_service import InvoiceService
                InvoiceService.mark_paid(invoice_id)
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
