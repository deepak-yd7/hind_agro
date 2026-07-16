"""
frontend/connection_setup.py
=============================
First-run connection wizard — shown before login if no db_config.json exists,
or when user clicks "Change Server" from login screen.

Two modes:
  • This is the SERVER  → host = localhost
  • This is a CLIENT   → user types server IP address
"""

from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QStackedWidget,
    QRadioButton, QButtonGroup, QSpinBox, QProgressBar,
    QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont

STYLE = """
QDialog, QWidget { background: #F5F7F2; }

QFrame#card {
    background: white;
    border-radius: 16px;
    border: 1px solid #D8ECD0;
}
QFrame#header_bar {
    background: #1E3A1E;
    border-radius: 12px 12px 0 0;
}
QLabel#page_title {
    font-size: 22px; font-weight: bold; color: #1A3A1A;
}
QLabel#page_sub {
    font-size: 13px; color: #7A9A7A;
}
QLabel#field_label {
    font-size: 12px; font-weight: bold; color: #2D4A2D;
}
QLabel#section_lbl {
    font-size: 13px; font-weight: bold; color: #1E3A1E;
    background: #EAF3E4; border-radius: 6px; padding: 6px 12px;
}
QLineEdit#field, QSpinBox#field {
    border: 1.5px solid #C8DFC0; border-radius: 8px;
    padding: 9px 13px; font-size: 13px;
    background: white; color: #1A3A1A;
}
QLineEdit#field:focus, QSpinBox#field:focus {
    border: 1.5px solid #2D7A2D; background: #FAFFFA;
}
QRadioButton {
    font-size: 14px; color: #1A3A1A; spacing: 10px;
}
QRadioButton::indicator {
    width: 20px; height: 20px;
    border: 2px solid #4A7C4A; border-radius: 10px;
}
QRadioButton::indicator:checked {
    background: #2D7A2D; border: 3px solid #2D7A2D;
}
QFrame#role_card {
    background: #F7FAF5; border-radius: 10px;
    border: 2px solid #C8DFC0; padding: 4px;
}
QFrame#role_card[selected=true] {
    border: 2px solid #2D7A2D; background: #EAF3E4;
}
QPushButton#primary_btn {
    background: #1E5C1E; color: white; border: none;
    border-radius: 9px; padding: 13px; font-size: 15px; font-weight: bold;
}
QPushButton#primary_btn:hover   { background: #2E7D2E; }
QPushButton#primary_btn:pressed { background: #144014; }
QPushButton#secondary_btn {
    background: #E8EDE8; color: #2D4A2D; border: none;
    border-radius: 9px; padding: 11px 22px; font-size: 13px;
}
QPushButton#secondary_btn:hover { background: #D0DAD0; }
QPushButton#test_btn {
    background: #1A5276; color: white; border: none;
    border-radius: 8px; padding: 10px 22px; font-size: 13px; font-weight: bold;
}
QPushButton#test_btn:hover  { background: #2471A3; }
QPushButton#test_btn:disabled { background: #AAAAAA; }
QLabel#status_ok  { color: #1D6A38; font-size: 13px; font-weight: bold; background: #E8F8EE; border-radius:6px; padding:6px 12px; }
QLabel#status_err { color: #C0392B; font-size: 12px; font-weight: bold; background: #FDECEA; border-radius:6px; padding:6px 12px; }
QProgressBar {
    border: none; border-radius: 4px; background: #E8EDE8; height: 6px;
}
QProgressBar::chunk { background: #2D7A2D; border-radius: 4px; }
"""


# ── Background test thread ────────────────────────────────────────────────────
class TestThread(QThread):
    result = pyqtSignal(bool, str)

    def __init__(self, host, port, database, user, password):
        super().__init__()
        self.host = host; self.port = port; self.database = database
        self.user = user; self.password = password

    def run(self):
        from backend.database import test_connection
        ok, msg = test_connection(self.host, self.port, self.database,
                                  self.user, self.password)
        self.result.emit(ok, msg)


# ─────────────────────────────────────────────────────────────────────────────
class ConnectionSetupDialog(QDialog):
    """
    Shown on first run or when 'Change Server' is clicked.
    Saves db_config.json and returns so main.py can init the DB.
    """
    connection_saved = pyqtSignal()

    def __init__(self, parent=None, first_run=True):
        super().__init__(parent)
        self.setWindowTitle("Database Connection Setup — Hind Agro Products ERP")
        self.setMinimumSize(700, 580)
        self.setStyleSheet(STYLE)
        self.first_run   = first_run
        self._test_ok    = False
        self._test_thread = None

        from backend.db_config import load_config
        self._cfg = load_config()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(36, 32, 36, 32)
        outer.setSpacing(20)

        # ── Title ─────────────────────────────────────────────────────────────
        title = QLabel("🌱  Database Connection Setup")
        title.setStyleSheet("font-size:24px;font-weight:bold;color:#1E3A1E;")
        sub = QLabel(
            "Configure which PostgreSQL server this machine connects to.\n"
            "One machine runs the database (Server). All others connect to it by IP (Client)."
        )
        sub.setStyleSheet("font-size:13px;color:#5A7A5A;")
        sub.setWordWrap(True)
        outer.addWidget(title)
        outer.addWidget(sub)

        # ── Step 1: Server or Client ───────────────────────────────────────────
        role_lbl = QLabel("Step 1 — What is this machine?")
        role_lbl.setObjectName("section_lbl")
        outer.addWidget(role_lbl)

        role_row = QHBoxLayout(); role_row.setSpacing(16)
        self._server_card = self._role_card(
            "🖥️  Server Machine",
            "The database runs HERE.\nUse this on the main office computer.",
            "server"
        )
        self._client_card = self._role_card(
            "💻  Client Machine",
            "Connect to the database on another computer.\nUse this on all other machines.",
            "client"
        )
        role_row.addWidget(self._server_card)
        role_row.addWidget(self._client_card)
        outer.addLayout(role_row)

        # ── Step 2: Connection details ─────────────────────────────────────────
        conn_lbl = QLabel("Step 2 — Connection Details")
        conn_lbl.setObjectName("section_lbl")
        outer.addWidget(conn_lbl)

        form_card = QFrame(); form_card.setObjectName("card")
        form_lay  = QVBoxLayout(form_card)
        form_lay.setContentsMargins(24, 20, 24, 20)
        form_lay.setSpacing(14)

        # Server IP (only shown for client)
        self._ip_row = QHBoxLayout()
        ip_lbl = QLabel("Server IP Address")
        ip_lbl.setObjectName("field_label")
        ip_lbl.setFixedWidth(140)
        self.ip_edit = QLineEdit()
        self.ip_edit.setObjectName("field")
        self.ip_edit.setPlaceholderText("e.g.  192.168.1.100")
        self.ip_edit.setFixedHeight(44)
        self.ip_edit.setText(self._cfg.get("host","") if self._cfg.get("host") != "localhost" else "")
        ip_hint = QLabel("📌 Find on server: run  ipconfig  (Windows) or  hostname -I  (Linux)")
        ip_hint.setStyleSheet("font-size:11px;color:#7A9A7A;")
        self._ip_row.addWidget(ip_lbl)
        self._ip_row.addWidget(self.ip_edit)
        ip_col = QVBoxLayout()
        ip_col.addLayout(self._ip_row)
        ip_col.addWidget(ip_hint)
        form_lay.addLayout(ip_col)

        # Port
        port_row = QHBoxLayout()
        port_lbl = QLabel("Port"); port_lbl.setObjectName("field_label"); port_lbl.setFixedWidth(140)
        self.port_spin = QSpinBox(); self.port_spin.setObjectName("field")
        self.port_spin.setRange(1, 65535); self.port_spin.setValue(int(self._cfg.get("port", 5432)))
        self.port_spin.setFixedHeight(44); self.port_spin.setFixedWidth(120)
        port_note = QLabel("Default PostgreSQL port is 5432")
        port_note.setStyleSheet("font-size:11px;color:#7A9A7A;")
        port_row.addWidget(port_lbl); port_row.addWidget(self.port_spin)
        port_row.addWidget(port_note); port_row.addStretch()
        form_lay.addLayout(port_row)

        # Database name
        db_row = QHBoxLayout()
        db_lbl = QLabel("Database Name"); db_lbl.setObjectName("field_label"); db_lbl.setFixedWidth(140)
        self.db_edit = QLineEdit(); self.db_edit.setObjectName("field")
        self.db_edit.setFixedHeight(44); self.db_edit.setText(self._cfg.get("database", "nursery_erp"))
        db_row.addWidget(db_lbl); db_row.addWidget(self.db_edit)
        form_lay.addLayout(db_row)

        # Username
        user_row = QHBoxLayout()
        user_lbl = QLabel("DB Username"); user_lbl.setObjectName("field_label"); user_lbl.setFixedWidth(140)
        self.user_edit = QLineEdit(); self.user_edit.setObjectName("field")
        self.user_edit.setFixedHeight(44); self.user_edit.setText(self._cfg.get("user","postgres"))
        user_row.addWidget(user_lbl); user_row.addWidget(self.user_edit)
        form_lay.addLayout(user_row)

        # Password
        pwd_row = QHBoxLayout()
        pwd_lbl = QLabel("DB Password"); pwd_lbl.setObjectName("field_label"); pwd_lbl.setFixedWidth(140)
        self.pwd_edit = QLineEdit(); self.pwd_edit.setObjectName("field")
        self.pwd_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd_edit.setFixedHeight(44)
        self.pwd_edit.setPlaceholderText("PostgreSQL password")
        self.pwd_edit.setText(self._cfg.get("password",""))
        pwd_row.addWidget(pwd_lbl); pwd_row.addWidget(self.pwd_edit)
        form_lay.addLayout(pwd_row)

        # Test button + status
        test_row = QHBoxLayout(); test_row.setSpacing(12)
        self.test_btn = QPushButton("🔌  Test Connection")
        self.test_btn.setObjectName("test_btn")
        self.test_btn.setFixedHeight(40)
        self.test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.test_btn.clicked.connect(self._test_connection)
        self.status_lbl = QLabel("")
        self.status_lbl.setVisible(False)
        self.status_lbl.setWordWrap(True)
        test_row.addWidget(self.test_btn)
        test_row.addWidget(self.status_lbl, stretch=1)
        form_lay.addLayout(test_row)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)   # indeterminate
        self._progress.setVisible(False)
        self._progress.setFixedHeight(6)
        form_lay.addWidget(self._progress)

        outer.addWidget(form_card)

        # ── Buttons ────────────────────────────────────────────────────────────
        btn_row = QHBoxLayout(); btn_row.setSpacing(12)
        if not first_run:
            cancel_btn = QPushButton("Cancel")
            cancel_btn.setObjectName("secondary_btn")
            cancel_btn.setFixedHeight(48)
            cancel_btn.clicked.connect(self.reject)
            btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        self.save_btn = QPushButton("Save & Connect  →")
        self.save_btn.setObjectName("primary_btn")
        self.save_btn.setFixedHeight(48)
        self.save_btn.setMinimumWidth(200)
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.clicked.connect(self._save_and_connect)
        btn_row.addWidget(self.save_btn)
        outer.addLayout(btn_row)

        # Default: select server if localhost, else client
        if self._cfg.get("host","localhost") == "localhost":
            self._select_role("server")
        else:
            self._select_role("client")

    # ── Role card builder ──────────────────────────────────────────────────────
    def _role_card(self, title: str, desc: str, role: str) -> QFrame:
        card = QFrame(); card.setObjectName("role_card")
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        lay  = QVBoxLayout(card); lay.setContentsMargins(20,16,20,16); lay.setSpacing(6)
        t = QLabel(title); t.setStyleSheet("font-size:15px;font-weight:bold;color:#1A3A1A;")
        d = QLabel(desc);  d.setStyleSheet("font-size:12px;color:#5A7A5A;"); d.setWordWrap(True)
        lay.addWidget(t); lay.addWidget(d)
        card.mousePressEvent = lambda _: self._select_role(role)
        card._role = role
        return card

    def _select_role(self, role: str):
        self._role = role
        for card in [self._server_card, self._client_card]:
            selected = card._role == role
            card.setProperty("selected", selected)
            card.style().unpolish(card); card.style().polish(card)
            card.setStyleSheet(
                f"QFrame#role_card {{ background:{'#EAF3E4' if selected else '#F7FAF5'};"
                f"border-radius:10px;border:2px solid {'#2D7A2D' if selected else '#C8DFC0'};padding:4px; }}"
            )
        # Show/hide IP field
        ip_visible = (role == "client")
        self.ip_edit.setVisible(ip_visible)
        self._ip_row.itemAt(0).widget().setVisible(ip_visible)  # label
        if role == "server":
            self.ip_edit.setText("")
        self._test_ok = False
        self.status_lbl.setVisible(False)

    # ── Test connection ────────────────────────────────────────────────────────
    def _test_connection(self):
        host = "localhost" if self._role == "server" else self.ip_edit.text().strip()
        if not host:
            self._show_status(False, "Please enter the server IP address.")
            return

        self.test_btn.setEnabled(False)
        self._progress.setVisible(True)
        self.status_lbl.setVisible(False)
        self._test_ok = False

        self._test_thread = TestThread(
            host=host,
            port=self.port_spin.value(),
            database=self.db_edit.text().strip(),
            user=self.user_edit.text().strip(),
            password=self.pwd_edit.text(),
        )
        self._test_thread.result.connect(self._on_test_result)
        self._test_thread.start()

    def _on_test_result(self, ok: bool, msg: str):
        self._progress.setVisible(False)
        self.test_btn.setEnabled(True)
        self._test_ok = ok
        self._show_status(ok, ("✅  " if ok else "❌  ") + msg)

    def _show_status(self, ok: bool, msg: str):
        self.status_lbl.setObjectName("status_ok" if ok else "status_err")
        self.status_lbl.setText(msg)
        self.status_lbl.setVisible(True)
        self.status_lbl.style().unpolish(self.status_lbl)
        self.status_lbl.style().polish(self.status_lbl)

    # ── Save & Connect ─────────────────────────────────────────────────────────
    def _save_and_connect(self):
        host = "localhost" if self._role == "server" else self.ip_edit.text().strip()
        if self._role == "client" and not host:
            self._show_status(False, "Please enter the server IP address.")
            return

        db   = self.db_edit.text().strip() or "nursery_erp"
        user = self.user_edit.text().strip() or "postgres"
        pwd  = self.pwd_edit.text()
        port = self.port_spin.value()

        # If not tested yet, test now before saving
        if not self._test_ok:
            reply = QMessageBox.question(
                self, "Not Tested",
                "You haven't tested the connection yet.\n"
                "Save anyway and try connecting?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        from backend.db_config import save_config
        save_config({
            "host":     host,
            "port":     port,
            "database": db,
            "user":     user,
            "password": pwd,
        })
        self.connection_saved.emit()
        self.accept()
