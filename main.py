"""
main.py — Hind Agro Products ERP entry point

Flow:
  1. Check if db_config.json exists
     → If NO  : show ConnectionSetupDialog (first run)
     → If YES : try to connect
       → If FAIL : show ConnectionSetupDialog with error
  2. Show LoginWindow
  3. On login success → show MainWindow (role-based)
"""
import sys
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Hind Agro Products ERP")
    app.setStyleSheet("""
        QComboBox QAbstractItemView {
            background: white;
            color: #111111;
            selection-background-color: #D6EDD6;
            selection-color: #111111;
            outline: 0;
        }
    """)

    from backend.db_config import is_configured, get_display_info

    def try_connect() -> bool:
        """Try to init DB. Returns True if successful."""
        try:
            from backend.database import init_db
            init_db()
            return True
        except Exception as e:
            return False

    def show_setup(first_run=True, error_msg=""):
        """Show connection setup dialog. Loops until connected or user quits."""
        from frontend.connection_setup import ConnectionSetupDialog
        dlg = ConnectionSetupDialog(first_run=first_run)
        if error_msg:
            dlg._show_status(False, f"Previous connection failed: {error_msg}")
        result = dlg.exec()
        if result:
            return try_connect()
        else:
            # User cancelled
            sys.exit(0)

    # ── Step 1: Connect to DB ──────────────────────────────────────────────────
    connected = False

    if not is_configured():
        # First run — no config file
        connected = show_setup(first_run=True)
    else:
        connected = try_connect()
        if not connected:
            # Config exists but connection failed
            from backend.db_config import get_display_info
            connected = show_setup(
                first_run=False,
                error_msg=f"Could not connect to {get_display_info()}"
            )

    if not connected:
        QMessageBox.critical(None, "Connection Failed",
            "Could not connect to the database.\nPlease check your settings and try again.")
        sys.exit(1)

    # ── Step 2: Install DB triggers + start real-time listener ───────────────
    try:
        from backend.realtime import install_triggers, start_listener
        install_triggers()   # idempotent — safe every run
        start_listener()     # background thread for LISTEN/NOTIFY
    except Exception as e:
        print(f"[Realtime] Could not start: {e}")

    # ── Step 3: Show Login ─────────────────────────────────────────────────────
    from frontend.login_window import LoginWindow
    from frontend.main_window  import MainWindow

    login_win = LoginWindow()

    def on_login(user):
        login_win.close()
        main_win = MainWindow(user)
        main_win.show()
        app._main_win = main_win

    login_win.login_success.connect(on_login)
    login_win.show()
    ret = app.exec()
    try:
        from backend.realtime import stop_listener
        stop_listener()
    except Exception:
        pass
    sys.exit(ret)


if __name__ == "__main__":
    main()
