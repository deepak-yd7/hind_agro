from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget,
    QPushButton, QLabel, QFrame, QSizePolicy, QMessageBox
)
from PyQt6.QtCore import Qt
from models.user_model import ROLE_OWNER, ROLE_ADMIN, ROLE_DISPATCH

STYLE = """
QMainWindow, QWidget#root { background-color: #F5F7F2; }
QWidget#sidebar { background-color: #2D4A2D; border-right: 1px solid #1E3A1E; }
QPushButton#nav_btn {
    background: transparent; color: #A8C4A8; border: none;
    text-align: left; padding: 12px 20px; font-size: 14px;
    border-radius: 8px; margin: 2px 8px;
}
QPushButton#nav_btn:hover { background-color: #3D5E3D; color: #E8F5E8; }
QPushButton#nav_btn[active=true] { background-color: #4A7C4A; color: #FFFFFF; font-weight: bold; }
QLabel#logo      { color: #E8F5E8; font-size: 20px; font-weight: bold; padding: 24px 20px 4px 20px; }
QLabel#logo_sub  { color: #7FA87F; font-size: 11px; padding: 0px 20px 4px 20px; }
QLabel#user_badge {
    color: white; font-size: 11px; font-weight: bold;
    padding: 4px 12px 16px 20px;
}
QFrame#divider   { background-color: #3D5E3D; max-height: 1px; margin: 8px 16px; }
QPushButton#logout_btn {
    background: #3D1E1E; color: #FFAAAA; border: none;
    border-radius: 6px; padding: 8px 16px; font-size: 12px; margin: 4px 12px;
}
QPushButton#logout_btn:hover { background: #5A2020; }
"""

# Pages and their role access
# (icon, label, page_class, module_path, allowed_roles)
ALL_NAV = [
    ("🌿", "Dashboard",   "DashboardPage",    "frontend.pages.dashboard_page",    [ROLE_OWNER, ROLE_ADMIN]),
    # ("🪴", "Inventory",   "InventoryPage",    "frontend.pages.inventory_page",    [ROLE_OWNER, ROLE_ADMIN]),
    ("🌱", "Production",  "ProductionPage",   "frontend.pages.production_page",   [ROLE_OWNER, ROLE_ADMIN]),
    ("👥", "Customers",   "CustomersPage",    "frontend.pages.customers_page",    [ROLE_OWNER]),
    ("📦", "Orders",      "OrdersPage",       "frontend.pages.orders_page",       [ROLE_OWNER]),
    ("🧾", "Invoices",    "InvoicesPage",     "frontend.pages.invoices_page",     [ROLE_OWNER]),
    ("👤", "Users",       "UsersPage",        "frontend.pages.users_page",        [ROLE_OWNER]),
    ("🚚", "Dispatch",    "DispatchPage",     "frontend.pages.dispatch_page",     [ROLE_OWNER, ROLE_DISPATCH]),
    ("🗓️", "Dispatch Planner", "DispatchPlannerPage", "frontend.pages.planner_page", [ROLE_OWNER, ROLE_DISPATCH]),
]

ROLE_BADGE = {
    ROLE_OWNER:    ("🌿 Owner",    "#27AE60"),
    ROLE_ADMIN:    ("🛠 Admin",    "#2980B9"),
    ROLE_DISPATCH: ("🚚 Dispatch", "#8E44AD"),
}


class MainWindow(QMainWindow):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setWindowTitle("Hind Agro Products ERP")
        self.setMinimumSize(1200, 750)
        self.showMaximized()
        self.setStyleSheet(STYLE)

        root = QWidget(); root.setObjectName("root")
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Sidebar ──────────────────────────────────────────────
        sidebar = QWidget(); sidebar.setObjectName("sidebar"); sidebar.setFixedWidth(224)
        sl = QVBoxLayout(sidebar); sl.setContentsMargins(0, 0, 0, 0); sl.setSpacing(0)

        logo = QLabel("🌱 Hind Agro Products"); logo.setObjectName("logo")
        logo_sub = QLabel("Agro Products ERP"); logo_sub.setObjectName("logo_sub")
        sl.addWidget(logo); sl.addWidget(logo_sub)

        # Role badge
        badge_text, badge_color = ROLE_BADGE.get(user.role, ("User", "#888"))
        role_lbl = QLabel(f"{badge_text}  ·  {user.full_name or user.username}")
        role_lbl.setObjectName("user_badge")
        role_lbl.setStyleSheet(f"color: {badge_color}; font-size: 11px; font-weight: bold; padding: 0px 20px 16px 20px;")
        sl.addWidget(role_lbl)

        divider = QFrame(); divider.setObjectName("divider"); divider.setFrameShape(QFrame.Shape.HLine)
        sl.addWidget(divider); sl.addSpacing(8)

        self.nav_buttons = []
        self.stack = QStackedWidget()

        # Filter nav items by role
        visible_nav = [(icon, label, cls, mod) for icon, label, cls, mod, roles in ALL_NAV
                       if user.role in roles]

        for i, (icon, label, cls_name, module) in enumerate(visible_nav):
            mod = __import__(module, fromlist=[cls_name])
            page = getattr(mod, cls_name)()
            self.stack.addWidget(page)

            btn = QPushButton(f"  {icon}  {label}")
            btn.setObjectName("nav_btn")
            btn.setProperty("active", i == 0)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, idx=i: self.switch_page(idx))
            sl.addWidget(btn)
            self.nav_buttons.append(btn)

        sl.addStretch()

        # Change Password button
        chpwd_btn = QPushButton("🔑  Change Password")
        chpwd_btn.setStyleSheet(
            "QPushButton { background:#1A3A2A; color:#A8C4A8; border:none;"
            " border-radius:6px; padding:8px 16px; font-size:12px; margin:2px 12px; }"
            "QPushButton:hover { background:#2A5A3A; color:#E8F5E8; }"
        )
        chpwd_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        chpwd_btn.clicked.connect(self.change_password)
        sl.addWidget(chpwd_btn)

        # Logout button
        logout_btn = QPushButton("⏻  Logout")
        logout_btn.setObjectName("logout_btn")
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_btn.clicked.connect(self.logout)
        sl.addWidget(logout_btn)

        # Server connection indicator
        from backend.db_config import get_display_info, load_config
        cfg = load_config()
        host = cfg.get("host","localhost")
        is_local = host == "localhost"
        conn_icon = "🖥️" if is_local else "🌐"
        conn_label = QLabel(f"{conn_icon}  {host}")
        conn_label.setStyleSheet(
            "color:#7FA87F; font-size:10px; padding:4px 20px 2px 20px;"
        )
        conn_label.setToolTip(f"Connected to: {get_display_info()}")
        sl.addWidget(conn_label)

        version = QLabel("v1.0.0")
        version.setStyleSheet("color: #5A7A5A; font-size: 10px; padding: 2px 20px 12px 20px;")
        sl.addWidget(version)

        layout.addWidget(sidebar)
        layout.addWidget(self.stack)

    def switch_page(self, index: int):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setProperty("active", i == index)
            btn.style().unpolish(btn); btn.style().polish(btn)

    def change_password(self):
        from frontend.forgot_password import ChangePasswordDialog
        dlg = ChangePasswordDialog(parent=self)
        dlg.exec()

    def logout(self):
        from services.auth_service import logout
        reply = QMessageBox.question(self, "Logout", "Are you sure you want to log out?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            logout()
            self.close()
            # Re-launch login window
            from frontend.login_window import LoginWindow
            self._login_win = LoginWindow()
            self._login_win.login_success.connect(self._reopen)
            self._login_win.show()

    def _reopen(self, user):
        self._login_win.close()
        win = MainWindow(user)
        win.show()
        self._new_win = win
