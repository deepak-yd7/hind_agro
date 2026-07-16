from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor

STYLE = """
/* ── Root background ─────────────────────────────────── */
QWidget#login_root {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #0F2210,
        stop:0.5 #1A3A1A,
        stop:1 #0A1A0A
    );
}

/* ── White login card ────────────────────────────────── */
QFrame#card {
    background-color: #FFFFFF;
    border-radius: 20px;
    border: none;
}
QFrame#card QLabel {
    color: #1A3A1A;
    background: transparent;
}

/* ── Input fields ────────────────────────────────────── */
QLineEdit#field {
    background-color: #FFFFFF;
    border: 2px solid #4A7C4A;
    border-radius: 10px;
    padding: 12px 16px;
    font-size: 15px;
    color: #0A1A0A;
    selection-background-color: #4A7C4A;
    selection-color: #FFFFFF;
}
QLineEdit#field:focus {
    border: 2.5px solid #1E7A1E;
    background-color: #FFFFFF;
    color: #0A1A0A;
}
QLineEdit#field:hover {
    border: 2px solid #2D6A2D;
    background-color: #FFFFFF;
}

/* ── Sign In button ──────────────────────────────────── */
QPushButton#login_btn {
    background-color: #1E5C1E;
    color: #FFFFFF;
    border: none;
    border-radius: 10px;
    padding: 14px;
    font-size: 16px;
    font-weight: bold;
    letter-spacing: 1px;
}
QPushButton#login_btn:hover   { background-color: #2E7D2E; }
QPushButton#login_btn:pressed { background-color: #144014; }

/* ── Error label ─────────────────────────────────────── */
QLabel#error_lbl {
    color: #C0392B;
    background: #FDECEA;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
    font-weight: bold;
}
"""


class LoginWindow(QWidget):
    login_success = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hind Agro Products ERP — Login")
        self.setMinimumSize(1100, 680)
        self.showMaximized()                    # ← full screen on launch
        self.setObjectName("login_root")
        self.setStyleSheet(STYLE)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── LEFT: brand panel ────────────────────────────────────────────────
        left = QWidget()
        left.setStyleSheet("background: transparent;")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(72, 0, 48, 0)
        left_layout.addStretch(2)

        # Logo
        logo_row = QHBoxLayout()
        logo_icon = QLabel("🌱")
        logo_icon.setStyleSheet("font-size: 48px;")
        logo_text = QLabel("Hind Agro Products")
        logo_text.setStyleSheet("font-size: 38px; font-weight: bold; color: #E8F5E8;")
        logo_row.addWidget(logo_icon)
        logo_row.addWidget(logo_text)
        logo_row.addStretch()
        left_layout.addLayout(logo_row)

        sub = QLabel("Agro Products ERP")
        sub.setStyleSheet("font-size: 15px; color: #7FC07F; margin-left: 4px; margin-bottom: 32px;")
        left_layout.addWidget(sub)

        tagline = QLabel("Manage your business with ease.\nInventory · Orders · Customers · Dispatch.")
        tagline.setStyleSheet("font-size: 16px; color: #A8CCA8; line-height: 1.8;")
        tagline.setWordWrap(True)
        left_layout.addWidget(tagline)

        left_layout.addSpacing(48)

        # Role info cards
        for icon, role, desc, color in [
            ("🌿", "Owner",    "Full access to all modules",     "#27AE60"),
            ("🛠",  "Admin",    "Inventory & User management",    "#2980B9"),
            ("🚚", "Dispatch", "Delivery status updates only",   "#8E44AD"),
        ]:
            row = QHBoxLayout()
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color}; font-size: 12px; min-width: 16px;")
            text = QLabel(f"  {icon}  {role}  —  {desc}")
            text.setStyleSheet(f"color: #C8E6C8; font-size: 13px;")
            row.addWidget(dot)
            row.addWidget(text)
            row.addStretch()
            left_layout.addLayout(row)
            left_layout.addSpacing(6)

        left_layout.addStretch(3)
        outer.addWidget(left, stretch=5)

        # ── RIGHT: white login card ──────────────────────────────────────────
        right = QWidget()
        right.setStyleSheet("background: transparent;")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(48, 0, 72, 0)
        right_layout.addStretch()

        card = QFrame()
        card.setObjectName("card")
        card.setFixedWidth(420)
        card.setAutoFillBackground(True)
        from PyQt6.QtGui import QPalette, QColor as QC
        pal = card.palette()
        pal.setColor(QPalette.ColorRole.Window, QC("#FFFFFF"))
        card.setPalette(pal)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(48)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 100))
        card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(44, 44, 44, 44)
        card_layout.setSpacing(0)

        # Card title
        card_title = QLabel("Welcome Back")
        card_title.setStyleSheet("font-size: 26px; font-weight: bold; color: #1A3A1A; margin-bottom: 6px; background: transparent;")
        card_sub = QLabel("Sign in to your account to continue")
        card_sub.setStyleSheet("font-size: 13px; color: #4A6A4A; margin-bottom: 32px; background: transparent;")
        card_layout.addWidget(card_title)
        card_layout.addWidget(card_sub)

        # Username
        u_label = QLabel("Username")
        u_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #1A3A1A; margin-bottom: 6px; background: transparent;")
        self.username_edit = QLineEdit()
        self.username_edit.setObjectName("field")
        self.username_edit.setPlaceholderText("Enter your username")
        self.username_edit.setFixedHeight(50)
        card_layout.addWidget(u_label)
        card_layout.addWidget(self.username_edit)
        card_layout.addSpacing(18)

        # Password
        p_label = QLabel("Password")
        p_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #1A3A1A; margin-bottom: 6px; background: transparent;")
        self.password_edit = QLineEdit()
        self.password_edit.setObjectName("field")
        self.password_edit.setPlaceholderText("Enter your password")
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setFixedHeight(50)
        self.password_edit.returnPressed.connect(self._do_login)
        card_layout.addWidget(p_label)
        card_layout.addWidget(self.password_edit)
        card_layout.addSpacing(10)

        # Error label (hidden by default)
        self.error_lbl = QLabel("")
        self.error_lbl.setObjectName("error_lbl")
        self.error_lbl.setVisible(False)
        self.error_lbl.setWordWrap(True)
        card_layout.addWidget(self.error_lbl)
        card_layout.addSpacing(24)

        # Sign In button
        login_btn = QPushButton("Sign In  →")
        login_btn.setObjectName("login_btn")
        login_btn.setFixedHeight(52)
        login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        login_btn.clicked.connect(self._do_login)
        card_layout.addWidget(login_btn)
        card_layout.addSpacing(20)

        # Hint
        hint = QLabel("Default login:  owner  /  owner123")
        hint.setStyleSheet("font-size: 12px; color: #4A7A4A; background: transparent;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(hint)
        card_layout.addSpacing(8)

        forgot_btn = QPushButton("Forgot Password?")
        forgot_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #2D7A2D; border: none;"
            " font-size: 12px; text-decoration: underline; }"
            "QPushButton:hover { color: #1A5C1A; }"
        )
        forgot_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        forgot_btn.clicked.connect(self._open_forgot_password)
        card_layout.addWidget(forgot_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # ── Connection info bar ──────────────────────────────────────────────
        card_layout.addSpacing(12)
        conn_bar = QFrame()
        conn_bar.setStyleSheet(
            "QFrame { background: #F0F7F0; border-radius: 8px; border: 1px solid #C8DFC0; }"
        )
        conn_lay = QHBoxLayout(conn_bar)
        conn_lay.setContentsMargins(12, 8, 12, 8)
        from backend.db_config import get_display_info
        conn_info = QLabel(f"🟢  Connected to: {get_display_info()}")
        conn_info.setStyleSheet("font-size: 11px; color: #2D5A2D; background: transparent; border: none;")
        change_btn = QPushButton("Change Server")
        change_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #1A5276; border: none;"
            " font-size: 11px; text-decoration: underline; }"
            "QPushButton:hover { color: #2980B9; }"
        )
        change_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        change_btn.clicked.connect(self._change_server)
        conn_lay.addWidget(conn_info)
        conn_lay.addStretch()
        conn_lay.addWidget(change_btn)
        card_layout.addWidget(conn_bar)

        right_layout.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)
        right_layout.addStretch()
        outer.addWidget(right, stretch=4)

    def _change_server(self):
        from frontend.connection_setup import ConnectionSetupDialog
        dlg = ConnectionSetupDialog(parent=self, first_run=False)
        if dlg.exec():
            try:
                from backend.database import init_db
                init_db()
                from backend.db_config import get_display_info
                QMessageBox.information(self, "Reconnected",
                    f"Now connected to: {get_display_info()}")
            except Exception as e:
                QMessageBox.critical(self, "Connection Failed", str(e))

    def _open_forgot_password(self):
        from frontend.forgot_password import ForgotPasswordDialog
        dlg = ForgotPasswordDialog(parent=self)
        dlg.exec()

    def _do_login(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text()

        if not username or not password:
            self._show_error("Please enter both username and password.")
            return
        try:
            from services.auth_service import login
            user = login(username, password)
            if user:
                self.error_lbl.setVisible(False)
                self.login_success.emit(user)
            else:
                self._show_error("Incorrect username or password. Please try again.")
                self.password_edit.clear()
                self.password_edit.setFocus()
        except Exception as e:
            self._show_error(f"Connection error: {e}")

    def _show_error(self, msg: str):
        self.error_lbl.setText(f"⚠  {msg}")
        self.error_lbl.setVisible(True)
