from backend.database import get_connection, hash_password
from models.user_model import AppUser, ROLE_OWNER, ROLE_ADMIN, ROLE_DISPATCH
from typing import Optional, List

# Holds the currently logged-in user for the session
_current_user: Optional[AppUser] = None


def login(username: str, password: str) -> Optional[AppUser]:
    global _current_user
    pw_hash = hash_password(password)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, username, password_hash, role, full_name,
                   COALESCE(phone,''), active, created_at
            FROM app_users
            WHERE username = %s AND password_hash = %s AND active = TRUE
        """, (username.strip(), pw_hash))
        row = cur.fetchone()
        if row:
            _current_user = AppUser(*row)
            return _current_user
    return None


def logout():
    global _current_user
    _current_user = None


def current_user() -> Optional[AppUser]:
    return _current_user


def is_owner() -> bool:
    return _current_user is not None and _current_user.role == ROLE_OWNER


def is_admin() -> bool:
    return _current_user is not None and _current_user.role in (ROLE_OWNER, ROLE_ADMIN)


def is_dispatch() -> bool:
    return _current_user is not None and _current_user.role == ROLE_DISPATCH


# ── User management (owner only) ──────────────────────────────────────────────

class UserManagementService:
    @staticmethod
    def get_all() -> List[AppUser]:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, username, password_hash, role, full_name,
                       COALESCE(phone,''), active, created_at
                FROM app_users ORDER BY role, username
            """)
            return [AppUser(*r) for r in cur.fetchall()]

    @staticmethod
    def create(username: str, password: str, role: str, full_name: str) -> AppUser:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO app_users (username, password_hash, role, full_name)
                VALUES (%s, %s, %s, %s) RETURNING id
            """, (username.strip(), hash_password(password), role, full_name.strip()))
            uid = cur.fetchone()[0]
        return AppUser(id=uid, username=username, role=role, full_name=full_name)

    @staticmethod
    def update_password(user_id: int, new_password: str):
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE app_users SET password_hash=%s WHERE id=%s",
                        (hash_password(new_password), user_id))

    @staticmethod
    def toggle_active(user_id: int):
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE app_users SET active = NOT active WHERE id=%s", (user_id,))

    @staticmethod
    def update_phone(user_id: int, phone: str):
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE app_users SET phone=%s WHERE id=%s", (phone.strip(), user_id))

    @staticmethod
    def update_password_by_phone(phone: str, new_password: str) -> bool:
        """Used after OTP verification — resets password for the user with this phone."""
        from backend.database import hash_password
        normalized = phone.strip().replace("+", "").replace(" ", "")
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM app_users WHERE REPLACE(REPLACE(phone,' ',''),'+','') = %s",
                        (normalized,))
            row = cur.fetchone()
            if not row:
                return False
            cur.execute("UPDATE app_users SET password_hash=%s WHERE id=%s",
                        (hash_password(new_password), row[0]))
            return True

    @staticmethod
    def get_by_phone(phone: str):
        """Find a user by phone number."""
        normalized = phone.strip().replace("+", "").replace(" ", "")
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, username, password_hash, role, full_name,
                       COALESCE(phone,''), active, created_at
                FROM app_users
                WHERE REPLACE(REPLACE(phone,' ',''),'+','') = %s AND active = TRUE
            """, (normalized,))
            row = cur.fetchone()
            return AppUser(*row) if row else None

    @staticmethod
    def delete(user_id: int):
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM app_users WHERE id=%s", (user_id,))

