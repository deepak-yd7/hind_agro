from datetime import datetime
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape

from collections import defaultdict

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QFileDialog,
    QCheckBox,
    QLabel,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from backend.realtime import db_signals
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
QTableWidget::item { padding: 0px 12px; color: #1A3A1A; border: none; }
QTableWidget::item:selected { background: #D6EDD6; color: #1A3A1A; }
QTableWidget::item:hover { background: #EEF8EE; }
QHeaderView::section {
    background: #EAF3E4; color: #2D5A2D; font-weight: bold; font-size: 13px;
    border: none; border-bottom: 2px solid #C8DFC0; padding: 12px 14px;
}
"""

ACTIVE_ORDER_STATUSES = {"Confirmed", "Dispatched", "Delivered"}
DELIVERY_STATUSES = ["Pending", "Out for Delivery", "Delivered", "Failed"]


class DispatchPlannerPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(TABLE_STYLE)

        main = QVBoxLayout(self)
        main.setContentsMargins(32, 28, 32, 28)
        main.setSpacing(18)

        header = QHBoxLayout()
        title_col = QVBoxLayout()
        title = QLabel("Dispatch Planner")
        title.setStyleSheet("font-size:28px;font-weight:bold;color:#1A3A1A;")
        sub = QLabel("Customer-wise dispatch quantities")
        sub.setStyleSheet("font-size:13px;color:#7A9A7A;")
        title_col.addWidget(title)
        title_col.addWidget(sub)
        header.addLayout(title_col)
        header.addStretch()
        main.addLayout(header)

        self.filter_bar = FilterBar(
            columns=["Customer", "Item", "Total"],
            dropdown_label="Delivery",
            dropdown_items=DELIVERY_STATUSES,
            auto_refresh_sec=5,
        )
        self.filter_bar.filter_changed.connect(self._on_filter)
        self.filter_bar.refresh_requested.connect(self.load_data)
        main.addWidget(self.filter_bar)

        self.summary_row = QHBoxLayout()
        self.summary_row.setSpacing(12)
        self._customer_badge = self._make_badge("Customers: 0", "#2D5A2D")
        self._item_badge = self._make_badge("Items: 0", "#1A5276")
        self._qty_badge = self._make_badge("Total Qty: 0", "#8E5A1A")
        self.hide_not_delivered_check = QCheckBox("Hide not delivered")
        self.hide_not_delivered_check.setCursor(Qt.CursorShape.PointingHandCursor)
        self.hide_not_delivered_check.setStyleSheet(
            "QCheckBox { color:#2D4A2D; font-size:13px; font-weight:600; spacing:8px; }"
            "QCheckBox::indicator { width:16px; height:16px; border:2px solid #4A7C4A; border-radius:4px; }"
            "QCheckBox::indicator:checked { background:#2D7A2D; border:2px solid #2D7A2D; }"
        )
        self.hide_not_delivered_check.stateChanged.connect(self._on_hide_not_delivered_changed)

        self.export_btn = QPushButton("Export Excel")
        self.export_btn.setFixedHeight(34)
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.setStyleSheet(
            "QPushButton { background:#1A5276; color:white; border:none; border-radius:7px;"
            " padding:0 16px; font-size:13px; font-weight:bold; }"
            "QPushButton:hover { background:#2471A3; }"
            "QPushButton:pressed { background:#154360; }"
        )
        self.export_btn.clicked.connect(self.export_excel)

        self.summary_row.addWidget(self._customer_badge)
        self.summary_row.addWidget(self._item_badge)
        self.summary_row.addWidget(self._qty_badge)
        self.summary_row.addStretch()
        self.summary_row.addWidget(self.hide_not_delivered_check)
        self.summary_row.addWidget(self.export_btn)
        main.addLayout(self.summary_row)

        self.table = QTableWidget()
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(
            TABLE_STYLE + "QTableWidget { alternate-background-color: #F5FAF3; }" + TABLE_SCROLLBAR_STYLE
        )
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main.addWidget(self.table)

        db_signals.orders_changed.connect(self._on_db_change)
        db_signals.customers_changed.connect(self._on_db_change)
        db_signals.plants_changed.connect(self._on_db_change)
        if hasattr(db_signals, "order_items_changed"):
            db_signals.order_items_changed.connect(self._on_db_change)

        self._export_headers = []
        self._export_rows = []
        self.load_data()

    def _make_badge(self, text, color):
        badge = QLabel(f"  {text}  ")
        badge.setStyleSheet(
            f"background:{color};color:white;border-radius:10px;"
            "font-size:12px;font-weight:bold;padding:5px 14px;"
        )
        return badge

    def _center_item(self, text, bold=False, color=""):
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        if bold:
            font = item.font()
            font.setBold(True)
            item.setFont(font)
        if color:
            item.setForeground(QColor(color))
        return item

    def _on_db_change(self, payload: str = ""):
        self.load_data()

    def _on_filter(self, search, col_idx, dropdown):
        self.load_data()

    def _on_hide_not_delivered_changed(self, *_):
        if self.hide_not_delivered_check.isChecked() and self.filter_bar.drop_combo:
            idx = self.filter_bar.drop_combo.findText("Delivered")
            if idx >= 0:
                self.filter_bar.drop_combo.setCurrentIndex(idx)
                return
        self.load_data()

    def _build_matrix(self, orders):
        item_names = []
        seen_items = set()
        matrix = defaultdict(lambda: defaultdict(int))

        for order in orders:
            customer = str(order.customer_name or "Unknown Customer").strip() or "Unknown Customer"
            for item in order.items:
                item_name = str(item.plant_name or "").strip()
                if not item_name:
                    item_name = f"Item {item.plant_id or ''}".strip()
                if item_name not in seen_items:
                    seen_items.add(item_name)
                    item_names.append(item_name)
                matrix[customer][item_name] += int(item.quantity or 0)

        item_names.sort(key=str.lower)
        customers = sorted(matrix.keys(), key=str.lower)
        return customers, item_names, matrix

    def _matches_search(self, customer, item_totals, row_total, item_names):
        query = self.filter_bar.get_search().lower()
        col = self.filter_bar.get_column()
        if not query:
            return True

        customer_text = customer.lower()
        items_text = " ".join(
            item.lower()
            for item in item_names
            if item_totals.get(item, 0)
        )
        total_text = str(row_total)

        if col == 1:
            return query in customer_text
        if col == 2:
            return query in items_text
        if col == 3:
            return query in total_text
        return query in customer_text or query in items_text or query in total_text

    def load_data(self):
        try:
            from services.user_service import OrderService
            from services.user_service import CustomerService

            all_orders = OrderService.get_all()
            all_customers = CustomerService.get_all()

            # ---------------- CUSTOMER MAP ----------------
            customer_address_map = {
                c.name: (
                    getattr(c, "phone", "N/A"),
                    getattr(c, "address_line1", "N/A"),
                    getattr(c, "district", "N/A"),
                    getattr(c, "state", "N/A"),
                    getattr(c, "pincode", "N/A"),
                )
                for c in all_customers
            }

            delivery_filter = self.filter_bar.get_dropdown()

            active_orders = [
                order for order in all_orders
                if (order.status or "") in ACTIVE_ORDER_STATUSES
            ]

            if self.hide_not_delivered_check.isChecked():
                delivery_filter = "Delivered"

            if delivery_filter:
                active_orders = [
                    order for order in active_orders
                    if (order.delivery_status or "Pending") == delivery_filter
                ]

            customers, item_names, matrix = self._build_matrix(active_orders)

            visible_customers = []
            for customer in customers:
                row_total = sum(matrix[customer].values())

                if self._matches_search(
                        customer,
                        matrix[customer],
                        row_total,
                        item_names
                ):
                    visible_customers.append(customer)

            self.filter_bar.set_count(len(visible_customers), len(customers))

            self._customer_badge.setText(
                f"  Customers: {len(visible_customers)}  "
            )

            self._item_badge.setText(
                f"  Items: {len(item_names)}  "
            )

            self._qty_badge.setText(
                f"  Total Qty: "
                f"{sum(sum(matrix[c].values()) for c in visible_customers)}  "
            )

            # ---------------- HEADERS ----------------
            headers = [
                          "Customer",
                          "Phone",
                          "Address",
                          "District",
                          "State",
                          "Pincode",
                      ] + item_names + ["Total"]

            self._export_headers = headers
            self._export_rows = []

            self.table.setColumnCount(len(headers))
            self.table.setHorizontalHeaderLabels(headers)

            column_widths = (
                    [180, 130, 180, 140, 120, 100]
                    + [110] * len(item_names)
                    + [120]
            )

            configure_scrollable_table(self.table, column_widths)

            self.table.setRowCount(len(visible_customers))

            # ---------------- FILL TABLE ----------------
            for row, customer in enumerate(visible_customers):

                self.table.setRowHeight(row, 46)

                phone, area, district, state, pincode = (
                    customer_address_map.get(
                        customer,
                        ("N/A", "N/A", "N/A", "N/A", "N/A")
                    )
                )

                # ---------------- FIXED COLUMNS ----------------
                self.table.setItem(row, 0, QTableWidgetItem(customer))
                self.table.setItem(row, 1, QTableWidgetItem(str(phone)))
                self.table.setItem(row, 2, QTableWidgetItem(str(area)))
                self.table.setItem(row, 3, QTableWidgetItem(str(district)))
                self.table.setItem(row, 4, QTableWidgetItem(str(state)))
                self.table.setItem(row, 5, QTableWidgetItem(str(pincode)))

                row_total = 0

                export_row = [
                    customer,
                    phone,
                    area,
                    district,
                    state,
                    pincode,
                ]

                # ---------------- ITEMS ----------------
                for col, item_name in enumerate(item_names, start=6):

                    qty = matrix[customer].get(item_name, 0)

                    row_total += qty

                    display = "" if qty == 0 else str(qty)

                    qty_item = self._center_item(display)

                    if qty:
                        qty_item.setForeground(QColor("#1A5276"))

                    self.table.setItem(row, col, qty_item)

                    export_row.append(qty)

                # ---------------- TOTAL ----------------
                total_col = len(headers) - 1

                self.table.setItem(
                    row,
                    total_col,
                    self._center_item(
                        row_total,
                        bold=True,
                        color="#1E5C1E",
                    ),
                )

                export_row.append(row_total)

                self._export_rows.append(export_row)

            fit_table_columns_to_contents(
                self.table,
                column_widths
            )

        except Exception as e:

            self.table.setColumnCount(1)

            self.table.setHorizontalHeaderLabels(
                ["Dispatch Planner"]
            )

            self.table.setRowCount(1)

            self.table.setRowHeight(0, 52)

            err = QTableWidgetItem(
                f"DB not connected: {e}"
            )

            err.setForeground(QColor("#C0392B"))

            self.table.setItem(0, 0, err)

    def export_excel(self):
        if not self._export_rows:
            QMessageBox.information(self, "Export Excel", "No dispatch planner entries to export.")
            return

        default_name = f"Dispatch_Planner_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Dispatch Planner",
            default_name,
            "Excel Workbook (*.xlsx)",
        )
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"

        try:
            self._write_xlsx(path, self._export_headers, self._export_rows)
            QMessageBox.information(self, "Export Excel", f"Dispatch planner exported:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    def _write_xlsx(self, path, headers, rows):
        sheet_xml = self._sheet_xml(headers, rows)
        with ZipFile(path, "w", ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>""")
            zf.writestr("_rels/.rels", """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""")
            zf.writestr("xl/workbook.xml", """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets><sheet name="Dispatch Planner" sheetId="1" r:id="rId1"/></sheets>
</workbook>""")
            zf.writestr("xl/_rels/workbook.xml.rels", """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>""")
            zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)

    def _sheet_xml(self, headers, rows):
        all_rows = [headers] + rows
        xml_rows = []
        for row_idx, row_values in enumerate(all_rows, start=1):
            cells = []
            for col_idx, value in enumerate(row_values, start=1):
                ref = f"{self._excel_col(col_idx)}{row_idx}"
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    cells.append(f'<c r="{ref}"><v>{value}</v></c>')
                else:
                    text = escape(str(value))
                    cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>')
            xml_rows.append(f'<row r="{row_idx}">{"".join(cells)}</row>')

        return """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<sheetData>""" + "".join(xml_rows) + """</sheetData>
</worksheet>"""

    def _excel_col(self, index):
        name = ""
        while index:
            index, rem = divmod(index - 1, 26)
            name = chr(65 + rem) + name
        return name
