"""
frontend/forgot_password.py
============================
Three-step forgot password flow:
  Step 1 → Enter phone number → Send OTP
  Step 2 → Enter OTP
  Step 3 → Enter new password + confirm

Also contains ChangePasswordDialog — used inside the app by logged-in users.
"""

from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QStackedWidget, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

STYLE = """
QDialog, QWidget { background: #F7FAF5; }
QFrame#card {
    background: white;
    border-radius: 14px;
    border: 1px solid #D8ECD0;
}
QLabel#step_title {
    font-size: 20px; font-weight: bold; color: #1A3A1A;
}
QLabel#step_sub {
    font-size: 12px; color: #7A9A7A;
}
QLabel#field_label {
    font-size: 13px; font-weight: bold; color: #2D4A2D;
}
QLineEdit#field {
    border: 1.5px solid #C8DFC0; border-radius: 8px;
    padding: 10px 14px; font-size: 14px;
    background: #F5FAF3; color: #1A3A1A;
}
QLineEdit#field:focus {
    border: 1.5px solid #2D7A2D; background: white;
}
QPushButton#primary_btn {
    background: #1E5C1E; color: white; border: none;
    border-radius: 8px; padding: 12px; font-size: 14px; font-weight: bold;
}
QPushButton#primary_btn:hover   { background: #2E7D2E; }
QPushButton#primary_btn:pressed { background: #144014; }
QPushButton#secondary_btn {
    background: #E8EDE8; color: #2D4A2D; border: none;
    border-radius: 8px; padding: 10px 20px; font-size: 13px;
}
QPushButton#secondary_btn:hover { background: #D0DAD0; }
QPushButton#resend_btn {
    background: transparent; color: #2D7A2D;
    border: none; font-size: 12px; text-decoration: underline;
}
QPushButton#resend_btn:hover { color: #1A5C1A; }
QPushButton#resend_btn:disabled { color: #AAAAAA; }
QLabel#error_lbl {
    color: #C0392B; background: #FDECEA;
    border-radius: 6px; padding: 6px 10px;
    font-size: 12px; font-weight: bold;
}
QLabel#success_lbl {
    color: #1D6A38; background: #E8F8EE;
    border-radius: 6px; padding: 6px 10px;
    font-size: 12px; font-weight: bold;
}
QLabel#otp_hint {
    font-size: 11px; color: #7A9A7A; font-style: italic;
}
QLabel#strength_lbl { font-size: 11px; font-weight: bold; }
"""


# ─────────────────────────────────────────────────────────────────────────────
#  Forgot Password Dialog  (3-step wizard)
# ─────────────────────────────────────────────────────────────────────────────

class ForgotPasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reset Password — Hind Agro Products")
        self.setFixedWidth(460)
        self.setStyleSheet(STYLE)
        self._verified_phone = ""
        self._resend_timer = None
        self._resend_countdown = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(0)

        # Progress indicator
        self._progress_row = self._build_progress()
        layout.addLayout(self._progress_row)
        layout.addSpacing(20)

        # Stacked pages
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_step1())
        self.stack.addWidget(self._build_step2())
        self.stack.addWidget(self._build_step3())
        self.stack.addWidget(self._build_step4_success())
        layout.addWidget(self.stack)

        self._set_step(0)

    # ── Progress bar ──────────────────────────────────────────────────────────
    def _build_progress(self):
        row = QHBoxLayout(); row.setSpacing(0)
        self._dots = []
        labels = ["Phone", "OTP", "Password", "Done"]
        for i, lbl in enumerate(labels):
            col = QVBoxLayout(); col.setSpacing(4); col.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            dot = QLabel("●")
            dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dot.setFixedSize(28, 28)
            txt = QLabel(lbl)
            txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
            txt.setStyleSheet("font-size:11px;color:#7A9A7A;")
            col.addWidget(dot)
            col.addWidget(txt)
            row.addLayout(col)
            self._dots.append((dot, txt))
            if i < len(labels) - 1:
                line = QFrame()
                line.setFrameShape(QFrame.Shape.HLine)
                line.setFixedHeight(2)
                line.setStyleSheet("background:#D8ECD0;margin-top:13px;")
                row.addWidget(line, stretch=1)
        return row

    def _set_step(self, step: int):
        self.stack.setCurrentIndex(step)
        for i, (dot, txt) in enumerate(self._dots):
            if i < step:
                dot.setStyleSheet("color:#27AE60;font-size:20px;")
                txt.setStyleSheet("font-size:11px;color:#27AE60;font-weight:bold;")
            elif i == step:
                dot.setStyleSheet("color:#1E5C1E;font-size:22px;font-weight:bold;")
                txt.setStyleSheet("font-size:11px;color:#1E5C1E;font-weight:bold;")
            else:
                dot.setStyleSheet("color:#C8DFC0;font-size:20px;")
                txt.setStyleSheet("font-size:11px;color:#AAAAAA;")

    # ── Step 1: Phone number ──────────────────────────────────────────────────
    def _build_step1(self):
        w = QWidget()
        lay = QVBoxLayout(w); lay.setSpacing(12)

        lay.addWidget(self._title("🔒 Forgot Password", "Enter your registered mobile number"))

        lay.addWidget(self._label("Mobile Number"))
        self.phone_edit = QLineEdit()
        self.phone_edit.setObjectName("field")
        self.phone_edit.setFixedHeight(48)
        self.phone_edit.setPlaceholderText("10-digit mobile number (e.g. 9876543210)")
        self.phone_edit.setMaxLength(13)
        self.phone_edit.returnPressed.connect(self._send_otp)
        lay.addWidget(self.phone_edit)

        hint = QLabel("We'll send a 6-digit OTP to this number.")
        hint.setObjectName("otp_hint")
        lay.addWidget(hint)

        self.step1_error = self._error_lbl()
        lay.addWidget(self.step1_error)
        lay.addSpacing(8)

        send_btn = self._primary_btn("Send OTP  →")
        send_btn.clicked.connect(self._send_otp)
        lay.addWidget(send_btn)

        back_btn = self._secondary_btn("← Back to Login")
        back_btn.clicked.connect(self.reject)
        lay.addWidget(back_btn)
        return w

    # ── Step 2: OTP entry ─────────────────────────────────────────────────────
    def _build_step2(self):
        w = QWidget()
        lay = QVBoxLayout(w); lay.setSpacing(12)

        self.step2_title = self._title("📱 Enter OTP", "")
        lay.addWidget(self.step2_title)
        self.step2_subtitle = QLabel("")
        self.step2_subtitle.setObjectName("step_sub")
        self.step2_subtitle.setWordWrap(True)
        lay.addWidget(self.step2_subtitle)

        # Dev mode OTP hint box
        self.dev_hint_box = QFrame()
        self.dev_hint_box.setStyleSheet(
            "QFrame { background:#FFF8E1; border:1.5px solid #FFD54F; border-radius:8px; padding:4px; }"
        )
        dhl = QVBoxLayout(self.dev_hint_box)
        dhl.setContentsMargins(12, 8, 12, 8)
        dev_title = QLabel("🛠  DEV MODE — OTP displayed below")
        dev_title.setStyleSheet("font-size:12px;font-weight:bold;color:#E65100;")
        self.dev_otp_label = QLabel("OTP: ------")
        self.dev_otp_label.setStyleSheet("font-size:22px;font-weight:bold;color:#1A3A1A;letter-spacing:6px;")
        self.dev_otp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dev_note = QLabel("Set OTP_DEV_MODE = False in services/otp_service.py\nto send real SMS instead.")
        dev_note.setStyleSheet("font-size:11px;color:#E65100;")
        dev_note.setWordWrap(True)
        dhl.addWidget(dev_title)
        dhl.addWidget(self.dev_otp_label)
        dhl.addWidget(dev_note)
        lay.addWidget(self.dev_hint_box)

        lay.addWidget(self._label("Enter 6-digit OTP"))
        self.otp_edit = QLineEdit()
        self.otp_edit.setObjectName("field")
        self.otp_edit.setFixedHeight(52)
        self.otp_edit.setPlaceholderText("• • • • • •")
        self.otp_edit.setMaxLength(6)
        self.otp_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.otp_edit.setStyleSheet(
            "QLineEdit#field { font-size:24px; letter-spacing:8px; font-weight:bold; }"
        )
        self.otp_edit.returnPressed.connect(self._verify_otp)
        lay.addWidget(self.otp_edit)

        # Timer + resend row
        timer_row = QHBoxLayout()
        self.timer_label = QLabel("OTP expires in 10:00")
        self.timer_label.setStyleSheet("font-size:12px;color:#7A9A7A;")
        self.resend_btn = QPushButton("Resend OTP")
        self.resend_btn.setObjectName("resend_btn")
        self.resend_btn.setEnabled(False)
        self.resend_btn.clicked.connect(self._resend_otp)
        timer_row.addWidget(self.timer_label)
        timer_row.addStretch()
        timer_row.addWidget(self.resend_btn)
        lay.addLayout(timer_row)

        self.step2_error = self._error_lbl()
        lay.addWidget(self.step2_error)
        lay.addSpacing(8)

        verify_btn = self._primary_btn("Verify OTP  →")
        verify_btn.clicked.connect(self._verify_otp)
        lay.addWidget(verify_btn)

        back_btn = self._secondary_btn("← Change Number")
        back_btn.clicked.connect(lambda: self._set_step(0))
        lay.addWidget(back_btn)
        return w

    # ── Step 3: New password ──────────────────────────────────────────────────
    def _build_step3(self):
        w = QWidget()
        lay = QVBoxLayout(w); lay.setSpacing(12)
        lay.addWidget(self._title("🔑 New Password", "Choose a strong new password"))

        lay.addWidget(self._label("New Password"))
        self.new_pass_edit = QLineEdit()
        self.new_pass_edit.setObjectName("field")
        self.new_pass_edit.setFixedHeight(48)
        self.new_pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_pass_edit.setPlaceholderText("Minimum 6 characters")
        self.new_pass_edit.textChanged.connect(self._check_strength)
        lay.addWidget(self.new_pass_edit)

        self.strength_lbl = QLabel("")
        self.strength_lbl.setObjectName("strength_lbl")
        lay.addWidget(self.strength_lbl)

        lay.addWidget(self._label("Confirm Password"))
        self.confirm_pass_edit = QLineEdit()
        self.confirm_pass_edit.setObjectName("field")
        self.confirm_pass_edit.setFixedHeight(48)
        self.confirm_pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_pass_edit.setPlaceholderText("Re-enter new password")
        self.confirm_pass_edit.returnPressed.connect(self._reset_password)
        lay.addWidget(self.confirm_pass_edit)

        self.step3_error = self._error_lbl()
        lay.addWidget(self.step3_error)
        lay.addSpacing(8)

        reset_btn = self._primary_btn("Reset Password  →")
        reset_btn.clicked.connect(self._reset_password)
        lay.addWidget(reset_btn)
        return w

    # ── Step 4: Success ───────────────────────────────────────────────────────
    def _build_step4_success(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(16)

        icon = QLabel("✅")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("font-size:52px;")
        lay.addWidget(icon)

        title = QLabel("Password Reset!")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size:22px;font-weight:bold;color:#1A3A1A;")
        lay.addWidget(title)

        sub = QLabel("Your password has been updated successfully.\nYou can now log in with your new password.")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet("font-size:13px;color:#7A9A7A;")
        sub.setWordWrap(True)
        lay.addWidget(sub)

        lay.addSpacing(16)
        login_btn = self._primary_btn("Go to Login")
        login_btn.clicked.connect(self.accept)
        lay.addWidget(login_btn)
        return w

    # ── Actions ───────────────────────────────────────────────────────────────
    def _send_otp(self):
        phone = self.phone_edit.text().strip()
        if not phone:
            self._show_error(self.step1_error, "Please enter your mobile number.")
            return

        # Check if phone is registered
        try:
            from services.auth_service import UserManagementService
            user = UserManagementService.get_by_phone(phone)
            if not user:
                self._show_error(self.step1_error,
                    "No account found with this number. "
                    "Ask the owner to add your phone in User Management.")
                return
        except Exception as e:
            self._show_error(self.step1_error, f"Error: {e}")
            return

        from services.otp_service import send_otp, OTP_DEV_MODE, OTP_EXPIRY_MINUTES
        success, msg = send_otp(phone)

        if success:
            self._verified_phone = phone
            # Update step 2 UI
            masked = phone[-4:].rjust(len(phone), "*")
            self.step2_subtitle.setText(
                f"OTP sent to +91 ••••••{phone[-4:]}.\nValid for {OTP_EXPIRY_MINUTES} minutes."
            )
            # Dev mode: fetch OTP from DB to display
            if OTP_DEV_MODE:
                self.dev_hint_box.setVisible(True)
                otp_code = self._get_latest_otp(phone)
                self.dev_otp_label.setText(f"OTP: {otp_code}")
            else:
                self.dev_hint_box.setVisible(False)

            self._start_countdown(OTP_EXPIRY_MINUTES * 60)
            self.step1_error.setVisible(False)
            self._set_step(1)
            self.otp_edit.clear()
            self.otp_edit.setFocus()
        else:
            self._show_error(self.step1_error, msg)

    def _resend_otp(self):
        self.otp_edit.clear()
        self._send_otp()

    def _verify_otp(self):
        otp = self.otp_edit.text().strip()
        if len(otp) != 6:
            self._show_error(self.step2_error, "Please enter the 6-digit OTP.")
            return

        from services.otp_service import verify_otp
        valid, msg = verify_otp(self._verified_phone, otp)

        if valid:
            self._stop_countdown()
            self.step2_error.setVisible(False)
            self._set_step(2)
            self.new_pass_edit.setFocus()
        else:
            self._show_error(self.step2_error, msg)
            self.otp_edit.selectAll()

    def _reset_password(self):
        new_pass     = self.new_pass_edit.text()
        confirm_pass = self.confirm_pass_edit.text()

        if len(new_pass) < 6:
            self._show_error(self.step3_error, "Password must be at least 6 characters.")
            return
        if new_pass != confirm_pass:
            self._show_error(self.step3_error, "Passwords do not match. Please try again.")
            self.confirm_pass_edit.clear()
            self.confirm_pass_edit.setFocus()
            return

        try:
            from services.auth_service import UserManagementService
            success = UserManagementService.update_password_by_phone(
                self._verified_phone, new_pass
            )
            if success:
                self._set_step(3)
            else:
                self._show_error(self.step3_error,
                    "Could not update password. Please try again.")
        except Exception as e:
            self._show_error(self.step3_error, f"Error: {e}")

    def _check_strength(self, password: str):
        if not password:
            self.strength_lbl.setText("")
            return
        score = 0
        if len(password) >= 6:  score += 1
        if len(password) >= 10: score += 1
        if any(c.isupper() for c in password): score += 1
        if any(c.isdigit() for c in password): score += 1
        if any(c in "!@#$%^&*" for c in password): score += 1
        levels = [
            (1, "Weak",   "#C0392B"),
            (2, "Fair",   "#E67E22"),
            (3, "Good",   "#F1C40F"),
            (4, "Strong", "#27AE60"),
            (5, "Very Strong", "#1D6A38"),
        ]
        for threshold, label, color in levels:
            if score <= threshold:
                self.strength_lbl.setText(f"Strength: {label}")
                self.strength_lbl.setStyleSheet(f"font-size:11px;font-weight:bold;color:{color};")
                return

    # ── Countdown timer ───────────────────────────────────────────────────────
    def _start_countdown(self, seconds: int):
        self._resend_countdown = seconds
        self.resend_btn.setEnabled(False)
        self._resend_timer = QTimer(self)
        self._resend_timer.timeout.connect(self._tick)
        self._resend_timer.start(1000)

    def _tick(self):
        self._resend_countdown -= 1
        mins = self._resend_countdown // 60
        secs = self._resend_countdown % 60
        self.timer_label.setText(f"OTP expires in {mins:02d}:{secs:02d}")
        if self._resend_countdown <= 0:
            self._stop_countdown()
            self.timer_label.setText("OTP expired.")
            self.resend_btn.setEnabled(True)

    def _stop_countdown(self):
        if self._resend_timer:
            self._resend_timer.stop()
            self._resend_timer = None

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _get_latest_otp(self, phone: str) -> str:
        """Fetch latest unused OTP from DB for dev mode display."""
        try:
            from services.otp_service import get_latest_otp_for_dev
            return get_latest_otp_for_dev(phone)
        except Exception:
            return "------"

    def _title(self, text, sub):
        w = QWidget()
        lay = QVBoxLayout(w); lay.setContentsMargins(0,0,0,0); lay.setSpacing(4)
        t = QLabel(text); t.setObjectName("step_title")
        s = QLabel(sub);  s.setObjectName("step_sub"); s.setWordWrap(True)
        lay.addWidget(t); lay.addWidget(s)
        return w

    def _label(self, text):
        l = QLabel(text); l.setObjectName("field_label")
        return l

    def _primary_btn(self, text):
        b = QPushButton(text); b.setObjectName("primary_btn")
        b.setFixedHeight(48); b.setCursor(Qt.CursorShape.PointingHandCursor)
        return b

    def _secondary_btn(self, text):
        b = QPushButton(text); b.setObjectName("secondary_btn")
        b.setFixedHeight(40); b.setCursor(Qt.CursorShape.PointingHandCursor)
        return b

    def _error_lbl(self):
        l = QLabel(""); l.setObjectName("error_lbl")
        l.setVisible(False); l.setWordWrap(True)
        return l

    def _show_error(self, label: QLabel, msg: str):
        label.setText(f"⚠  {msg}")
        label.setVisible(True)

    def closeEvent(self, event):
        self._stop_countdown()
        super().closeEvent(event)


# ─────────────────────────────────────────────────────────────────────────────
#  Change Password Dialog  (for logged-in users inside the app)
# ─────────────────────────────────────────────────────────────────────────────

class ChangePasswordDialog(QDialog):
    """
    Allows a logged-in user to change their own password.
    Requires current password first, then new password.
    Accessible from the sidebar or settings.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Change Password")
        self.setFixedWidth(420)
        self.setStyleSheet(STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(14)

        # Title
        title = QLabel("🔑 Change Password")
        title.setStyleSheet("font-size:20px;font-weight:bold;color:#1A3A1A;")
        sub = QLabel("Enter your current password, then choose a new one.")
        sub.setStyleSheet("font-size:12px;color:#7A9A7A;")
        sub.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(sub)

        # Current password
        layout.addWidget(self._lbl("Current Password"))
        self.current_edit = QLineEdit()
        self.current_edit.setObjectName("field")
        self.current_edit.setFixedHeight(46)
        self.current_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.current_edit.setPlaceholderText("Enter your current password")
        layout.addWidget(self.current_edit)

        # New password
        layout.addWidget(self._lbl("New Password"))
        self.new_edit = QLineEdit()
        self.new_edit.setObjectName("field")
        self.new_edit.setFixedHeight(46)
        self.new_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_edit.setPlaceholderText("Minimum 6 characters")
        self.new_edit.textChanged.connect(self._strength)
        layout.addWidget(self.new_edit)

        self.strength_lbl = QLabel("")
        self.strength_lbl.setObjectName("strength_lbl")
        layout.addWidget(self.strength_lbl)

        # Confirm password
        layout.addWidget(self._lbl("Confirm New Password"))
        self.confirm_edit = QLineEdit()
        self.confirm_edit.setObjectName("field")
        self.confirm_edit.setFixedHeight(46)
        self.confirm_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_edit.setPlaceholderText("Re-enter new password")
        self.confirm_edit.returnPressed.connect(self._save)
        layout.addWidget(self.confirm_edit)

        self.error_lbl = QLabel("")
        self.error_lbl.setObjectName("error_lbl")
        self.error_lbl.setVisible(False)
        self.error_lbl.setWordWrap(True)
        layout.addWidget(self.error_lbl)

        # Buttons
        btns = QHBoxLayout(); btns.setSpacing(10)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondary_btn")
        cancel.setFixedHeight(42)
        cancel.clicked.connect(self.reject)
        save = QPushButton("Update Password")
        save.setObjectName("primary_btn")
        save.setFixedHeight(42)
        save.setCursor(Qt.CursorShape.PointingHandCursor)
        save.clicked.connect(self._save)
        btns.addWidget(cancel)
        btns.addWidget(save)
        layout.addLayout(btns)

    def _lbl(self, text):
        l = QLabel(text); l.setObjectName("field_label")
        return l

    def _strength(self, password: str):
        if not password:
            self.strength_lbl.setText(""); return
        score = sum([
            len(password) >= 6,
            len(password) >= 10,
            any(c.isupper() for c in password),
            any(c.isdigit() for c in password),
            any(c in "!@#$%^&*" for c in password),
        ])
        for threshold, label, color in [
            (1,"Weak","#C0392B"),(2,"Fair","#E67E22"),
            (3,"Good","#F1C40F"),(4,"Strong","#27AE60"),(5,"Very Strong","#1D6A38")
        ]:
            if score <= threshold:
                self.strength_lbl.setText(f"Strength: {label}")
                self.strength_lbl.setStyleSheet(f"font-size:11px;font-weight:bold;color:{color};")
                return

    def _save(self):
        from services.auth_service import current_user, UserManagementService
        from backend.database import hash_password

        user     = current_user()
        cur_pass = self.current_edit.text()
        new_pass = self.new_edit.text()
        confirm  = self.confirm_edit.text()

        if not cur_pass:
            self._err("Please enter your current password."); return
        if hash_password(cur_pass) != user.password_hash:
            self._err("Current password is incorrect."); return
        if len(new_pass) < 6:
            self._err("New password must be at least 6 characters."); return
        if new_pass != confirm:
            self._err("Passwords do not match.")
            self.confirm_edit.clear(); return
        if new_pass == cur_pass:
            self._err("New password must be different from current password."); return

        try:
            UserManagementService.update_password(user.id, new_pass)
            QMessageBox.information(self, "Success",
                "✅ Password updated successfully!\nPlease use your new password next time you log in.")
            self.accept()
        except Exception as e:
            self._err(f"Error: {e}")

    def _err(self, msg: str):
        self.error_lbl.setText(f"⚠  {msg}")
        self.error_lbl.setVisible(True)
