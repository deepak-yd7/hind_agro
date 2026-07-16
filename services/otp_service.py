"""
services/otp_service.py
========================
OTP via Twilio SMS.

DEV MODE (default, OTP_DEV_MODE = True):
  - No SMS is sent
  - OTP is printed in terminal AND shown in a yellow box on screen
  - Works immediately with zero setup

PRODUCTION MODE (OTP_DEV_MODE = False):
  - Real SMS sent via Twilio
  - Fill TWILIO_CONFIG below with your credentials
  - pip install twilio

How to get Twilio credentials:
  1. Sign up at https://twilio.com (free trial gives $15 credit)
  2. Console Dashboard -> copy Account SID and Auth Token
  3. Buy/get a phone number -> copy it (e.g. +12015551234)
  4. Paste all three below and set OTP_DEV_MODE = False
"""

import random
import string
from datetime import datetime, timedelta
from backend.database import get_connection

# ── Twilio config — fill in when ready ───────────────────────────────────────
OTP_DEV_MODE = True          # ← set False when Twilio is configured

TWILIO_CONFIG = {
    "account_sid": "YOUR_TWILIO_ACCOUNT_SID",   # e.g. "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    "auth_token":  "YOUR_TWILIO_AUTH_TOKEN",    # e.g. "your_auth_token_here"
    "from_number": "YOUR_TWILIO_PHONE_NUMBER",  # e.g. "+12015551234"
}

# ── OTP settings ──────────────────────────────────────────────────────────────
OTP_LENGTH         = 6
OTP_EXPIRY_MINUTES = 10


def generate_otp() -> str:
    return "".join(random.choices(string.digits, k=OTP_LENGTH))


def send_otp(phone: str) -> tuple[bool, str]:
    """
    Generates OTP, saves to DB, sends via Twilio SMS (or shows in dev mode).
    Returns: (success: bool, message: str)
    """
    phone = _normalize(phone)
    if not phone or len(phone) < 12:   # must be 91XXXXXXXXXX = 12 digits
        return False, "Please enter a valid 10-digit mobile number."

    otp        = generate_otp()
    expires_at = datetime.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)

    # Save to DB — invalidate previous OTPs for this phone first
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE otp_sessions SET used=TRUE WHERE phone=%s AND used=FALSE",
                (phone,)
            )
            cur.execute("""
                INSERT INTO otp_sessions (phone, otp_code, purpose, expires_at)
                VALUES (%s, %s, 'reset_password', %s)
            """, (phone, otp, expires_at))
    except Exception as e:
        return False, f"Database error: {e}"

    # Send
    if OTP_DEV_MODE:
        _dev_print(phone, otp)
        return True, "DEV_MODE"          # caller checks for this string
    else:
        return _send_twilio(phone, otp)


def verify_otp(phone: str, entered_otp: str) -> tuple[bool, str]:
    """
    Verifies the OTP. Marks it used on success.
    Returns: (valid: bool, message: str)
    """
    phone = _normalize(phone)
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, otp_code, expires_at
                FROM otp_sessions
                WHERE phone=%s AND used=FALSE
                ORDER BY created_at DESC LIMIT 1
            """, (phone,))
            row = cur.fetchone()

            if not row:
                return False, "No OTP found. Please request a new one."

            otp_id, stored_otp, expires_at = row

            if datetime.now() > expires_at:
                cur.execute("UPDATE otp_sessions SET used=TRUE WHERE id=%s", (otp_id,))
                return False, "OTP expired. Please request a new one."

            if entered_otp.strip() != stored_otp:
                return False, "Incorrect OTP. Please check and try again."

            cur.execute("UPDATE otp_sessions SET used=TRUE WHERE id=%s", (otp_id,))
            return True, "OTP verified successfully."

    except Exception as e:
        return False, f"Verification error: {e}"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalize(phone: str) -> str:
    """Always returns 91XXXXXXXXXX (12 chars) or raw if unrecognised."""
    p = phone.strip().replace("+", "").replace(" ", "").replace("-", "")
    if p.startswith("91") and len(p) == 12:
        return p
    if len(p) == 10:
        return "91" + p
    return p


def _send_twilio(phone: str, otp: str) -> tuple[bool, str]:
    """Send OTP SMS via Twilio."""
    try:
        from twilio.rest import Client
    except ImportError:
        return False, "Twilio not installed. Run: pip install twilio"

    try:
        sid   = TWILIO_CONFIG["account_sid"]
        token = TWILIO_CONFIG["auth_token"]
        from_ = TWILIO_CONFIG["from_number"]

        if not sid or sid.startswith("YOUR_"):
            return False, "Twilio credentials not configured in services/otp_service.py"

        client = Client(sid, token)
        to_number = f"+{phone}"   # Twilio needs +91XXXXXXXXXX format

        message = client.messages.create(
            body=(
                f"Your Hind Agro Products OTP is: {otp}\n"
                f"Valid for {OTP_EXPIRY_MINUTES} minutes.\n"
                f"Do not share this code with anyone."
            ),
            from_=from_,
            to=to_number,
        )
        print(f"[OTP] Twilio SMS sent. SID={message.sid} Status={message.status}")
        return True, f"OTP sent to +91 ••••••{phone[-4:]}. Valid for {OTP_EXPIRY_MINUTES} minutes."

    except Exception as e:
        err = str(e)
        print(f"[OTP] Twilio error: {err}")
        # Give user-friendly messages for common Twilio errors
        if "authenticate" in err.lower() or "20003" in err:
            return False, "Twilio authentication failed. Check Account SID and Auth Token."
        if "not a valid phone" in err.lower() or "21211" in err:
            return False, "Invalid phone number format."
        if "unverified" in err.lower() or "21608" in err:
            return False, "Phone number not verified in Twilio trial account."
        return False, f"SMS failed: {err}"


def _dev_print(phone: str, otp: str):
    """Print OTP clearly in terminal for dev/testing."""
    print("\n" + "=" * 52)
    print(f"  [DEV MODE] OTP for +{phone}")
    print(f"  CODE : {otp}")
    print(f"  Valid: {OTP_EXPIRY_MINUTES} minutes")
    print("=" * 52 + "\n")


def get_latest_otp_for_dev(phone: str) -> str:
    """Fetch latest unused OTP from DB — only used in dev mode UI display."""
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT otp_code FROM otp_sessions
                WHERE phone=%s AND used=FALSE
                ORDER BY created_at DESC LIMIT 1
            """, (_normalize(phone),))
            row = cur.fetchone()
            return row[0] if row else "------"
    except Exception:
        return "------"
