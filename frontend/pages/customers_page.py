from backend.realtime import db_signals
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QDialog, QFormLayout, QTextEdit, QMessageBox,
    QDoubleSpinBox,
    QHeaderView, QSizePolicy, QFrame
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QFont
from backend.database import get_table_columns
from frontend.filter_bar import FilterBar
from frontend.table_utils import (
    TABLE_SCROLLBAR_STYLE,
    configure_scrollable_table,
    fit_table_columns_to_contents,
)

TABLE_STYLE = """
QWidget { font-family: 'Segoe UI', Arial, sans-serif; }
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
QLabel { font-size: 13px; color: #2D4A2D; font-weight: 500; }
QLineEdit, QTextEdit, QDoubleSpinBox {
    border: 1.5px solid #C8DFC0; border-radius: 6px;
    padding: 8px 12px; font-size: 13px; background: white; color: #1A3A1A;
}
QLineEdit:focus, QTextEdit:focus, QDoubleSpinBox:focus { border: 1.5px solid #4A7C4A; }
QFrame#section_frame {
    background: #EAF3E4; border-radius: 8px; border: none;
}
"""


class CustomerDialog(QDialog):
    def __init__(self, customer=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Customer" if not customer else "Edit Customer")
        self.setMinimumWidth(500)
        self.setStyleSheet(DIALOG_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        title = QLabel("Add New Customer" if not customer else "Edit Customer")
        title.setStyleSheet("font-size:18px;font-weight:bold;color:#1E3A1E;")
        layout.addWidget(title)

        # ── Basic Info ────────────────────────────────────────────────────────
        basic_lbl = QLabel("👤  Basic Info")
        basic_lbl.setStyleSheet(
            "font-size:12px;font-weight:bold;color:#2D4A2D;"
            "background:#EAF3E4;border-radius:6px;padding:5px 10px;"
        )
        layout.addWidget(basic_lbl)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.name_edit  = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Ramesh Kumar")
        self.name_edit.setFixedHeight(38)

        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("e.g. 9876543210")
        self.phone_edit.setFixedHeight(38)

        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("e.g. ramesh@email.com")
        self.email_edit.setFixedHeight(38)

        self.gst_edit = QLineEdit()
        self.gst_edit.setPlaceholderText("e.g. 27ABCDE1234F1Z5")
        self.gst_edit.setFixedHeight(38)

        self.pan_edit = QLineEdit()
        self.pan_edit.setPlaceholderText("e.g. ABCDE1234F")
        self.pan_edit.setFixedHeight(38)

        self.discount_spin = QDoubleSpinBox()
        self.discount_spin.setRange(0, 100)
        self.discount_spin.setDecimals(2)
        self.discount_spin.setSuffix(" %")
        self.discount_spin.setFixedHeight(38)

        form.addRow("Name *", self.name_edit)
        form.addRow("Phone", self.phone_edit)
        form.addRow("Email", self.email_edit)
        form.addRow("GST No", self.gst_edit)
        form.addRow("PAN No", self.pan_edit)
        form.addRow("Default Discount", self.discount_spin)
        layout.addLayout(form)

        # ── Address ───────────────────────────────────────────────────────────
        addr_lbl = QLabel("📍  Address")
        addr_lbl.setStyleSheet(
            "font-size:12px;font-weight:bold;color:#2D4A2D;"
            "background:#EAF3E4;border-radius:6px;padding:5px 10px;"
        )
        layout.addWidget(addr_lbl)

        addr_form = QFormLayout()
        addr_form.setSpacing(10)
        addr_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.addr1_edit = QLineEdit()
        self.addr1_edit.setPlaceholderText("Street / Village / Locality")
        self.addr1_edit.setFixedHeight(38)

        self.district_edit = QLineEdit()
        self.district_edit.setPlaceholderText("e.g. Lucknow")
        self.district_edit.setFixedHeight(38)

        self.state_edit = QLineEdit()
        self.state_edit.setPlaceholderText("e.g. Uttar Pradesh")
        self.state_edit.setFixedHeight(38)

        self.pincode_edit = QLineEdit()
        self.pincode_edit.setPlaceholderText("e.g. 226001")
        self.pincode_edit.setFixedHeight(38)
        self.pincode_edit.setMaxLength(10)

        addr_form.addRow("Address",  self.addr1_edit)
        addr_form.addRow("District", self.district_edit)
        addr_form.addRow("State",    self.state_edit)
        addr_form.addRow("Pincode",  self.pincode_edit)
        layout.addLayout(addr_form)

        # Pre-fill if editing
        if customer:
            self.name_edit.setText(customer.name or "")
            self.phone_edit.setText(customer.phone or "")
            self.email_edit.setText(customer.email or "")

            self.gst_edit.setText(getattr(customer, "gst_no", "") or "")
            self.pan_edit.setText(getattr(customer, "pan_no", "") or "")
            self.discount_spin.setValue(float(getattr(customer, "discount_percent", 0) or 0))

            self.addr1_edit.setText(getattr(customer, "address_line1", "") or "")
            self.district_edit.setText(getattr(customer, "district", "") or "")
            self.state_edit.setText(getattr(customer, "state", "") or "")
            self.pincode_edit.setText(getattr(customer, "pincode", "") or "")

        # ── Buttons ───────────────────────────────────────────────────────────
        btns = QHBoxLayout(); btns.setSpacing(10)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(40)
        cancel_btn.setStyleSheet(
            "QPushButton{background:#E8EDE8;color:#2D4A2D;border:none;"
            "border-radius:8px;padding:0 22px;font-size:13px;}"
            "QPushButton:hover{background:#D0DAD0;}"
        )
        save_btn = QPushButton("💾  Save Customer")
        save_btn.setFixedHeight(40)
        save_btn.setStyleSheet(
            "QPushButton{background:#2D4A2D;color:white;border:none;"
            "border-radius:8px;padding:0 26px;font-size:13px;font-weight:bold;}"
            "QPushButton:hover{background:#3D6B3D;}"
            "QPushButton:pressed{background:#1E3A1E;}"
        )
        cancel_btn.clicked.connect(self.reject)
        save_btn.clicked.connect(self.accept)
        btns.addStretch()
        btns.addWidget(cancel_btn)
        btns.addWidget(save_btn)
        layout.addLayout(btns)


# ─────────────────────────────────────────────────────────────────────────────

class CustomersPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(TABLE_STYLE)

        main = QVBoxLayout(self)
        main.setContentsMargins(32, 28, 32, 28)
        main.setSpacing(16)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        tc  = QVBoxLayout(); tc.setSpacing(2)
        title = QLabel("Customers")
        title.setStyleSheet("font-size:28px;font-weight:bold;color:#1A3A1A;")
        sub = QLabel("Manage your business customer accounts.")
        sub.setStyleSheet("font-size:13px;color:#7A9A7A;")
        tc.addWidget(title); tc.addWidget(sub)
        hdr.addLayout(tc)
        hdr.addStretch()

        add_btn = QPushButton("＋  Add Customer")
        add_btn.setFixedHeight(40)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet(
            "QPushButton{background:#2D4A2D;color:white;border:none;"
            "border-radius:8px;padding:0 22px;font-size:14px;font-weight:bold;}"
            "QPushButton:hover{background:#3D6B3D;}"
            "QPushButton:pressed{background:#1E3A1E;}"
        )
        add_btn.clicked.connect(self.add_customer)
        hdr.addWidget(add_btn)
        main.addLayout(hdr)

        # ── Filter bar ────────────────────────────────────────────────────────
        self.filter_bar = FilterBar(
            columns=[
                "Name", "Phone", "Email", "GST No", "PAN No", "Discount", "District", "State", "Pincode"],
            auto_refresh_sec=5,
        )
        self.filter_bar.filter_changed.connect(self._on_filter)
        self.filter_bar.refresh_requested.connect(self.load_data)
        main.addWidget(self.filter_bar)

        # ── Table ─────────────────────────────────────────────────────────────
        # ── Table ─────────────────────────────────────────────────────────────
        self.table = QTableWidget()

        self.table.setColumnCount(11)

        self.table.setHorizontalHeaderLabels([
            "ID",
            "Name",
            "Phone",
            "Email",
            "GST No",
            "PAN No",
            "Discount",
            "Address",
            "District",
            "State",
            "Actions"
        ])

        self._column_min_widths = [80, 220, 150, 260, 180, 160, 100, 300, 160, 160, 220]
        configure_scrollable_table(self.table, self._column_min_widths)

        # ================= TABLE STYLE =================
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )

        self.table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )

        self.table.verticalHeader().setVisible(False)

        self.table.setAlternatingRowColors(True)

        self.table.setShowGrid(False)

        self.table.setSortingEnabled(True)

        self.table.verticalHeader().setDefaultSectionSize(54)

        self.table.setStyleSheet(
            TABLE_STYLE +
            """
            QTableWidget{
                alternate-background-color:#F5FAF3;
            }
            """
            + TABLE_SCROLLBAR_STYLE
        )

        self.table.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        main.addWidget(self.table)

        # ── Real-time DB updates ──────────────────────────────────────────────
        db_signals.customers_changed.connect(self._on_db_change)

        self.load_data()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _ci(self, text: str, center=True) -> QTableWidgetItem:
        item = QTableWidgetItem(str(text))
        if center:
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

    def _on_filter(self, search, col_idx, dropdown):
        self.load_data()

    def _on_db_change(self, payload: str = ""):
        """Called instantly when customers table changes on any connected machine."""
        self.load_data()

    # ── Data loading ──────────────────────────────────────────────────────────

    def load_data(self):
        try:
            from services.user_service import CustomerService

            query    = self.filter_bar.get_search()
            col      = self.filter_bar.get_column()
            all_custs = CustomerService.get_all()

            if query:
                ql = query.lower()
                def match(cu):
                    fields = [
                        cu.name or "",
                        cu.phone or "",
                        cu.email or "",
                        cu.gst_no or "",
                        cu.pan_no or "",
                        str(cu.discount_percent or ""),
                        cu.district or "",
                        cu.state or "",
                        cu.pincode or ""
                    ]
                    if col == 0:
                        return any(ql in f.lower() for f in fields)
                    elif col <= len(fields):
                        return ql in fields[col - 1].lower()
                    return True
                customers = [cu for cu in all_custs if match(cu)]
            else:
                customers = all_custs

            self.filter_bar.set_count(len(customers), len(all_custs))

            self.table.setRowCount(0)
            self.table.setRowCount(len(customers))

            for row, c in enumerate(customers):
                self.table.setRowHeight(row, 54)

                self.table.setItem(row, 0, self._ci(str(c.id or "")))

                name_item = QTableWidgetItem(c.name or "")
                name_item.setFont(QFont("Segoe UI", 13, QFont.Weight.Medium))
                self.table.setItem(row, 1, name_item)

                self.table.setItem(row, 2, self._ci(c.phone or ""))
                self.table.setItem(row, 3, QTableWidgetItem(c.email or ""))
                self.table.setItem(row, 4, QTableWidgetItem(c.gst_no or ""))
                self.table.setItem(row, 5, QTableWidgetItem(c.pan_no or ""))
                self.table.setItem(row, 6, self._ci(f"{float(c.discount_percent or 0):.2f}%"))
                self.table.setItem(row, 7, QTableWidgetItem(c.address_line1 or ""))
                self.table.setItem(row, 8, self._ci(c.district or ""))
                self.table.setItem(row, 9, self._ci(c.state or ""))

                # ── Action buttons ────────────────────────────────────────────
                bw = QWidget()
                bw.setStyleSheet("background:transparent;")
                bl = QHBoxLayout(bw)
                bl.setContentsMargins(8, 6, 8, 6)
                bl.setSpacing(8)
                bl.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

                edit_btn = QPushButton("Edit")
                edit_btn.setFixedSize(QSize(78, 34))
                edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                edit_btn.setStyleSheet(
                    "QPushButton{background:#2E7D32;color:white;font-size:13px;"
                    "font-weight:bold;border:none;border-radius:6px;}"
                    "QPushButton:hover{background:#43A047;}"
                    "QPushButton:pressed{background:#1B5E20;}"
                )
                edit_btn.clicked.connect(lambda _, cu=c: self.edit_customer(cu))

                del_btn = QPushButton("Delete")
                del_btn.setFixedSize(QSize(78, 34))
                del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                del_btn.setStyleSheet(
                    "QPushButton{background:#C62828;color:white;font-size:13px;"
                    "font-weight:bold;border:none;border-radius:6px;}"
                    "QPushButton:hover{background:#EF5350;}"
                    "QPushButton:pressed{background:#8E0000;}"
                )
                del_btn.clicked.connect(lambda _, cid=c.id: self.delete_customer(cid))

                bl.addWidget(edit_btn)
                bl.addWidget(del_btn)
                self.table.setCellWidget(row, 10, bw)

            fit_table_columns_to_contents(self.table, self._column_min_widths)

        except Exception as e:
            self.table.setRowCount(1)
            self.table.setRowHeight(0, 54)
            err = QTableWidgetItem(f"⚠  Error: {e}")
            err.setForeground(QColor("#C0392B"))
            self.table.setItem(0, 0, err)

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def add_customer(self):
        dlg = CustomerDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                from services.user_service import CustomerService
                from models.user_model import Customer
                cu = Customer(
                    name=dlg.name_edit.text().strip(),
                    phone=dlg.phone_edit.text().strip(),
                    email=dlg.email_edit.text().strip(),

                    gst_no=dlg.gst_edit.text().strip(),
                    pan_no=dlg.pan_edit.text().strip(),
                    discount_percent=dlg.discount_spin.value(),

                    address_line1=dlg.addr1_edit.text().strip(),
                    district=dlg.district_edit.text().strip(),
                    state=dlg.state_edit.text().strip(),
                    pincode=dlg.pincode_edit.text().strip(),
                )
                if not cu.name:
                    QMessageBox.warning(self, "Validation", "Customer name is required.")
                    return
                CustomerService.save(cu)
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def edit_customer(self, customer):
        dlg = CustomerDialog(customer=customer, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                from services.user_service import CustomerService
                customer.name = dlg.name_edit.text().strip()
                customer.phone = dlg.phone_edit.text().strip()
                customer.email = dlg.email_edit.text().strip()

                customer.gst_no = dlg.gst_edit.text().strip()
                customer.pan_no = dlg.pan_edit.text().strip()
                customer.discount_percent = dlg.discount_spin.value()

                customer.address_line1 = dlg.addr1_edit.text().strip()
                customer.district = dlg.district_edit.text().strip()
                customer.state = dlg.state_edit.text().strip()
                customer.pincode = dlg.pincode_edit.text().strip()
                CustomerService.save(customer)
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def delete_customer(self, cid):
        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Delete this customer?\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                from services.user_service import CustomerService
                CustomerService.delete(cid)
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
