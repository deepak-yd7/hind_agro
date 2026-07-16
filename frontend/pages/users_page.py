from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QDialog, QFormLayout, QLineEdit, QComboBox, QMessageBox,
    QHeaderView, QSizePolicy
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
QTableWidget::item:hover    { background: #EEF8EE; }
QHeaderView::section {
    background: #EAF3E4; color: #2D5A2D; font-weight: bold; font-size: 13px;
    border: none; border-bottom: 2px solid #C8DFC0; padding: 12px 14px;
}
"""

ROLE_COLORS = {"owner": "#27AE60", "admin": "#2980B9", "dispatch": "#8E44AD"}
ROLE_LABELS = {"owner": "🌿 Owner", "admin": "🛠 Admin", "dispatch": "🚚 Dispatch"}


class AddUserDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New User")
        self.setMinimumWidth(420)
        self.setStyleSheet("""
            QDialog { background: #F7FAF5; }
            QLabel { font-size: 13px; color: #2D4A2D; font-weight: 500; }
            QLineEdit, QComboBox {
                border: 1.5px solid #C8DFC0; border-radius: 6px;
                padding: 8px 12px; font-size: 13px; background: white; color: #1A3A1A;
            }
            QLineEdit:focus, QComboBox:focus { border: 1.5px solid #4A7C4A; }
            QComboBox QAbstractItemView {
                background: white;
                color: #111111;
                selection-background-color: #D6EDD6;
                selection-color: #111111;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(0)

        title = QLabel("Add New User")
        title.setStyleSheet("font-size:18px;font-weight:bold;color:#1E3A1E;margin-bottom:16px;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setContentsMargins(0, 0, 0, 16)

        self.fullname_edit = QLineEdit(); self.fullname_edit.setPlaceholderText("e.g. Ramesh Kumar")
        self.username_edit = QLineEdit(); self.username_edit.setPlaceholderText("e.g. ramesh")
        self.password_edit = QLineEdit(); self.password_edit.setPlaceholderText("Minimum 6 characters")
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.phone_edit = QLineEdit(); self.phone_edit.setPlaceholderText("10-digit mobile (for OTP reset)")
        self.role_combo = QComboBox()
        self.role_combo.addItems(["admin", "dispatch"])  # owner cannot create another owner

        form.addRow("Full Name *",  self.fullname_edit)
        form.addRow("Username *",   self.username_edit)
        form.addRow("Password *",   self.password_edit)
        form.addRow("Mobile (OTP)", self.phone_edit)
        form.addRow("Role *",       self.role_combo)
        layout.addLayout(form)

        btns = QHBoxLayout(); btns.setSpacing(10)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(38)
        cancel_btn.setStyleSheet(
            "QPushButton { background:#E8EDE8;color:#2D4A2D;border:none;border-radius:7px;padding:0 20px;font-size:13px; }"
            "QPushButton:hover { background:#D0DAD0; }"
        )
        save_btn = QPushButton("Create User")
        save_btn.setFixedHeight(38)
        save_btn.setStyleSheet(
            "QPushButton { background:#2D4A2D;color:white;border:none;border-radius:7px;padding:0 24px;font-size:13px;font-weight:bold; }"
            "QPushButton:hover { background:#3D6B3D; }"
        )
        cancel_btn.clicked.connect(self.reject)
        save_btn.clicked.connect(self.accept)
        btns.addStretch(); btns.addWidget(cancel_btn); btns.addWidget(save_btn)
        layout.addLayout(btns)


class UsersPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(TABLE_STYLE)

        main = QVBoxLayout(self)
        main.setContentsMargins(32, 28, 32, 28)
        main.setSpacing(18)

        header = QHBoxLayout()
        title_col = QVBoxLayout()
        title = QLabel("User Management")
        title.setStyleSheet("font-size:28px;font-weight:bold;color:#1A3A1A;")
        sub = QLabel("Manage login accounts and roles")
        sub.setStyleSheet("font-size:13px;color:#7A9A7A;")
        title_col.addWidget(title)
        title_col.addWidget(sub)
        header.addLayout(title_col)
        header.addStretch()
        add_btn = QPushButton("＋  Add User")
        add_btn.setFixedHeight(38)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet(
            "QPushButton { background:#2D4A2D;color:white;border:none;border-radius:8px;padding:0 22px;font-size:14px;font-weight:bold; }"
            "QPushButton:hover { background:#3D6B3D; }"
        )
        add_btn.clicked.connect(self.add_user)
        header.addWidget(add_btn)
        main.addLayout(header)

        self.filter_bar = FilterBar(
            columns=["Full Name","Username","Mobile"],
            dropdown_label="Role",
            dropdown_items=["owner","admin","dispatch"],
            auto_refresh_sec=5,
        )
        self.filter_bar.filter_changed.connect(self._on_filter)
        self.filter_bar.refresh_requested.connect(self.load_data)
        main.addWidget(self.filter_bar)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "Full Name", "Username", "Mobile", "Role", "Active", "Actions"])
        self._column_min_widths = [60, 220, 190, 140, 130, 110, 200]
        configure_scrollable_table(self.table, self._column_min_widths)

        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(
            TABLE_STYLE + "QTableWidget { alternate-background-color: #F5FAF3; }" + TABLE_SCROLLBAR_STYLE
        )
        main.addWidget(self.table)

        # ── Real-time DB updates (fires within 1 sec of any DB change) ────
        db_signals.users_changed.connect(self._on_db_change)

        self.load_data()

    def _center_item(self, text):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

    def _on_db_change(self, payload: str = ""):
        self.load_data()

    def _on_filter(self, search, col_idx, dropdown):
        self.load_data()

    def load_data(self):
        try:
            from services.auth_service import UserManagementService, current_user
            all_users = UserManagementService.get_all()
            query    = self.filter_bar.get_search()
            col      = self.filter_bar.get_column()
            dropdown = self.filter_bar.get_dropdown()

            def match(u):
                if dropdown and u.role != dropdown: return False
                if query:
                    ql = query.lower()
                    fields = [str(u.full_name or ""), str(u.username or ""),
                              str(getattr(u,"phone","") or "")]
                    if col == 0:
                        return any(ql in f.lower() for f in fields)
                    elif col <= len(fields):
                        return ql in fields[col-1].lower()
                return True

            users = [u for u in all_users if match(u)]
            self.filter_bar.set_count(len(users), len(all_users))
            self.table.setRowCount(0)
            self.table.setRowCount(len(users))
            me = current_user()

            for row, u in enumerate(users):
                self.table.setRowHeight(row, 52)
                self.table.setItem(row, 0, self._center_item(str(u.id)))
                name_item = QTableWidgetItem(u.full_name or u.username)
                name_item.setFont(QFont("Segoe UI", 13, QFont.Weight.Medium))
                self.table.setItem(row, 1, name_item)
                self.table.setItem(row, 2, QTableWidgetItem(u.username))

                # Phone — show last 10 digits nicely
                ph = getattr(u, "phone", "") or ""
                if ph.startswith("91") and len(ph) == 12:
                    ph_display = ph[2:]  # strip 91
                else:
                    ph_display = ph
                ph_item = self._center_item(ph_display or "—  not set")
                if not ph_display:
                    ph_item.setForeground(QColor("#AAAAAA"))
                self.table.setItem(row, 3, ph_item)

                role_item = self._center_item(ROLE_LABELS.get(u.role, u.role))
                role_item.setForeground(QColor(ROLE_COLORS.get(u.role, "#666")))
                f = role_item.font(); f.setBold(True); role_item.setFont(f)
                self.table.setItem(row, 4, role_item)

                active_item = self._center_item("✅ Active" if u.active else "❌ Inactive")
                active_item.setForeground(QColor("#27AE60" if u.active else "#C0392B"))
                self.table.setItem(row, 5, active_item)

                # Actions
                btn_widget = QWidget()
                btn_widget.setStyleSheet("background: transparent;")
                bl = QHBoxLayout(btn_widget)
                bl.setContentsMargins(8, 6, 8, 6)
                bl.setSpacing(8)
                bl.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

                toggle_btn = QPushButton("Disable" if u.active else "Enable")
                toggle_btn.setFixedSize(QSize(80, 34))
                toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                tc = "#E67E22" if u.active else "#27AE60"
                th = "#F39C12" if u.active else "#2ECC71"
                toggle_btn.setStyleSheet(
                    f"QPushButton {{ background-color:{tc};color:white;font-size:12px;font-weight:bold;border:none;border-radius:6px; }}"
                    f"QPushButton:hover {{ background-color:{th}; }}"
                )

                del_btn = QPushButton("Delete")
                del_btn.setFixedSize(QSize(75, 34))
                del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                del_btn.setStyleSheet(
                    "QPushButton { background-color:#C62828;color:white;font-size:12px;font-weight:bold;border:none;border-radius:6px; }"
                    "QPushButton:hover { background-color:#EF5350; }"
                )

                is_self = me and me.id == u.id
                is_owner = u.role == "owner"

                if is_self or is_owner:
                    toggle_btn.setEnabled(False)
                    toggle_btn.setStyleSheet("QPushButton { background:#D0D0D0;color:#888;border:none;border-radius:6px; }")
                if is_self or is_owner:
                    del_btn.setEnabled(False)
                    del_btn.setStyleSheet("QPushButton { background:#D0D0D0;color:#888;border:none;border-radius:6px; }")

                toggle_btn.clicked.connect(lambda _, uid=u.id: self.toggle_user(uid))
                del_btn.clicked.connect(lambda _, uid=u.id: self.delete_user(uid))

                bl.addWidget(toggle_btn)
                bl.addWidget(del_btn)
                self.table.setCellWidget(row, 6, btn_widget)

            fit_table_columns_to_contents(self.table, self._column_min_widths)

        except Exception as e:
            self.table.setRowCount(1)
            err = QTableWidgetItem(f"⚠  Error: {e}")
            err.setForeground(QColor("#C0392B"))
            self.table.setItem(0, 0, err)

    def add_user(self):
        dlg = AddUserDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                from services.auth_service import UserManagementService
                name = dlg.fullname_edit.text().strip()
                user = dlg.username_edit.text().strip()
                pwd  = dlg.password_edit.text()
                role = dlg.role_combo.currentText()
                if not user or not pwd:
                    QMessageBox.warning(self, "Validation", "Username and password are required.")
                    return
                if len(pwd) < 6:
                    QMessageBox.warning(self, "Validation", "Password must be at least 6 characters.")
                    return
                phone = dlg.phone_edit.text().strip().replace("+","").replace(" ","")
                if phone and not phone.startswith("91") and len(phone)==10:
                    phone = "91" + phone
                new_user = UserManagementService.create(user, pwd, role, name)
                if phone and new_user:
                    UserManagementService.update_phone(new_user.id, phone)
                self.load_data()
                QMessageBox.information(self, "Created", f"User '{user}' created successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def toggle_user(self, uid):
        try:
            from services.auth_service import UserManagementService
            UserManagementService.toggle_active(uid)
            self.load_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def delete_user(self, uid):
        reply = QMessageBox.question(self, "Confirm", "Delete this user? They will no longer be able to log in.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                from services.auth_service import UserManagementService
                UserManagementService.delete(uid)
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
