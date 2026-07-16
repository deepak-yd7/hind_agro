"""
backend/realtime.py
====================
Real-time database change detection using PostgreSQL LISTEN / NOTIFY.

HOW IT WORKS:
  1. PostgreSQL triggers fire NOTIFY on INSERT/UPDATE/DELETE on each table.
  2. A background thread listens on a dedicated connection.
  3. When a notification arrives it emits a Qt signal within 1 second.
  4. Pages connect to these signals and call load_data() immediately.

No polling — pure event-driven. Changes from ANY machine on the network
(another user, a script, direct DB edit) instantly appear on all clients.

TABLES WATCHED:
  plants, seeds, containers, customers, orders, order_items, invoices, app_users
"""

import select
import threading
import psycopg2
import psycopg2.extensions
from PyQt6.QtCore import QObject, pyqtSignal
from backend.db_config import get_db_config


# ── Signals ───────────────────────────────────────────────────────────────────
class DBSignals(QObject):
    """Qt signal hub — one signal per watched table."""
    plants_changed          = pyqtSignal(str)
    seeds_changed           = pyqtSignal(str)
    containers_changed      = pyqtSignal(str)
    customers_changed       = pyqtSignal(str)
    orders_changed          = pyqtSignal(str)
    order_items_changed     = pyqtSignal(str)
    invoices_changed        = pyqtSignal(str)
    users_changed           = pyqtSignal(str)
    production_lots_changed = pyqtSignal(str)
    production_stages_changed = pyqtSignal(str)
    any_changed             = pyqtSignal(str)

# Global singleton — import and use anywhere
db_signals = DBSignals()

# ── Watched channels ──────────────────────────────────────────────────────────
CHANNELS = {
    "plants_changed":            db_signals.plants_changed,
    "seeds_changed":             db_signals.seeds_changed,
    "containers_changed":        db_signals.containers_changed,
    "customers_changed":         db_signals.customers_changed,
    "orders_changed":            db_signals.orders_changed,
    "order_items_changed":       db_signals.order_items_changed,
    "invoices_changed":          db_signals.invoices_changed,
    "users_changed":             db_signals.users_changed,
    "production_lots_changed":   db_signals.production_lots_changed,
    "production_stages_changed": db_signals.production_stages_changed,
}

# ── Trigger SQL ───────────────────────────────────────────────────────────────
_TRIGGER_FUNC_SQL = """
CREATE OR REPLACE FUNCTION notify_table_change()
RETURNS trigger AS $$
BEGIN
    PERFORM pg_notify(TG_TABLE_NAME || '_changed', TG_OP);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

_TABLES = [
    "plants", "seeds", "containers",
    "customers", "orders", "order_items", "invoices", "app_users",
    "production_lots", "production_stages",
]

_TRIGGER_SQL_TEMPLATE = """
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'trg_{table}_realtime'
          AND tgrelid = '{table}'::regclass
    ) THEN
        CREATE TRIGGER trg_{table}_realtime
        AFTER INSERT OR UPDATE OR DELETE ON {table}
        FOR EACH ROW EXECUTE FUNCTION notify_table_change();
    END IF;
END;
$$;
"""


def install_triggers():
    """
    Install the notify function + triggers on all watched tables.
    Safe to call multiple times (idempotent).
    Called once at app startup.
    """
    cfg  = get_db_config()
    conn = psycopg2.connect(**cfg)
    conn.autocommit = True
    cur  = conn.cursor()
    try:
        cur.execute(_TRIGGER_FUNC_SQL)
        for table in _TABLES:
            try:
                cur.execute(_TRIGGER_SQL_TEMPLATE.format(table=table))
            except Exception as e:
                print(f"[Realtime] Trigger for {table}: {e}")
        print("[Realtime] ✅ Triggers installed on all tables")
    except Exception as e:
        print(f"[Realtime] WARNING: Could not install triggers: {e}")
    finally:
        cur.close()
        conn.close()


# ── Listener thread ────────────────────────────────────────────────────────────
class _ListenerThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True, name="DBListener")
        self._stop_event = threading.Event()
        self._conn       = None

    def run(self):
        cfg = get_db_config()
        try:
            self._conn = psycopg2.connect(**cfg)
            self._conn.set_isolation_level(
                psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT
            )
            cur = self._conn.cursor()
            for channel in CHANNELS:
                cur.execute(f"LISTEN {channel};")
            print(f"[Realtime] Listening on {len(CHANNELS)} channels")

            while not self._stop_event.is_set():
                # select() waits up to 1 second for a notification
                r, _, _ = select.select([self._conn], [], [], 1.0)
                if r:
                    self._conn.poll()
                    while self._conn.notifies:
                        notify  = self._conn.notifies.pop(0)
                        channel = notify.channel
                        payload = notify.payload or "CHANGE"
                        print(f"[Realtime] 🔔 {channel} → {payload}")
                        # Emit specific signal
                        if channel in CHANNELS:
                            CHANNELS[channel].emit(payload)
                        # Also emit the catch-all
                        table = channel.replace("_changed","")
                        db_signals.any_changed.emit(f"{table}:{payload}")

        except Exception as e:
            print(f"[Realtime] Listener error: {e}")
        finally:
            if self._conn:
                try:
                    self._conn.close()
                except Exception:
                    pass
            print("[Realtime] Listener thread stopped")

    def stop(self):
        self._stop_event.set()


# ── Public API ─────────────────────────────────────────────────────────────────
_listener: _ListenerThread = None


def start_listener():
    """Start the background LISTEN thread. Call once at app startup."""
    global _listener
    if _listener and _listener.is_alive():
        return
    _listener = _ListenerThread()
    _listener.start()


def stop_listener():
    """Stop the background thread. Call at app shutdown."""
    global _listener
    if _listener:
        _listener.stop()
        _listener = None
