import hashlib
import psycopg2
from psycopg2 import pool
from contextlib import contextmanager
from backend.db_config import get_db_config, load_config

connection_pool = None


def init_db():
    global connection_pool
    cfg = get_db_config()
    connection_pool = psycopg2.pool.ThreadedConnectionPool(1, 10, **cfg)

    # Execution order is critical to prevent Foreign Key relation errors
    _create_base_tables()         # 1. Independent tables (seeds, customers, etc.)
    _create_production_tables()   # 2. Depends on seeds
    _create_transaction_tables()  # 3. Depends on customers & production_lots

    _create_otp_table()
    _seed_default_owner()


def test_connection(host, port, database, user, password) -> tuple[bool, str]:
    """Test a connection without affecting the global pool. Returns (ok, message)."""
    try:
        conn = psycopg2.connect(
            host=host, port=int(port),
            database=database, user=user, password=password,
            connect_timeout=5,
        )
        conn.close()
        return True, "Connection successful!"
    except psycopg2.OperationalError as e:
        msg = str(e).strip()
        if "password authentication" in msg:
            return False, "Wrong password."
        if "does not exist" in msg:
            return False, f"Database '{database}' does not exist on the server."
        if "Connection refused" in msg or "could not connect" in msg.lower():
            return False, f"Cannot reach server at {host}:{port}.\nCheck IP address and that PostgreSQL is running."
        if "timeout" in msg.lower():
            return False, f"Connection timed out — {host} is not reachable.\nCheck the IP and firewall."
        return False, f"Connection failed:\n{msg}"
    except Exception as e:
        return False, str(e)


@contextmanager
def get_connection():
    conn = connection_pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        connection_pool.putconn(conn)


def hash_password(password: str) -> str:
    salt = "greenleaf_erp_salt"
    return hashlib.sha256((salt + password).encode()).hexdigest()


def _create_base_tables():
    """Stage 1: Core tables that do not depend on other tables."""
    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS app_users (
                id            SERIAL PRIMARY KEY,
                username      VARCHAR(80) UNIQUE NOT NULL,
                password_hash VARCHAR(256) NOT NULL,
                role          VARCHAR(20) DEFAULT 'admin',
                full_name     VARCHAR(150),
                phone         VARCHAR(20) DEFAULT '',
                active        BOOLEAN DEFAULT TRUE,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id              SERIAL PRIMARY KEY,
                name            VARCHAR(150) NOT NULL,
                phone           VARCHAR(20),
                email           VARCHAR(150),
                gst_no          VARCHAR(30) DEFAULT '',
                pan_no          VARCHAR(20) DEFAULT '',
                discount_percent NUMERIC(5,2) DEFAULT 0,
                address_line1   TEXT DEFAULT '',
                district        VARCHAR(100) DEFAULT '',
                state           VARCHAR(100) DEFAULT '',
                pincode         VARCHAR(20) DEFAULT '',
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS discount_percent NUMERIC(5,2) DEFAULT 0")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS plants (
                id                  SERIAL PRIMARY KEY,
                name                VARCHAR(150) NOT NULL,
                category            VARCHAR(100),
                description         TEXT,
                unit_price          NUMERIC(10,2) NOT NULL DEFAULT 0,
                stock_qty           INTEGER NOT NULL DEFAULT 0,
                low_stock_threshold INTEGER DEFAULT 10,
                container_type      VARCHAR(50) DEFAULT '',
                plants_per_unit     INTEGER DEFAULT 1,
                container_stock     INTEGER DEFAULT 0,
                created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("ALTER TABLE plants ADD COLUMN IF NOT EXISTS container_type VARCHAR(50) DEFAULT ''")
        cur.execute("ALTER TABLE plants ADD COLUMN IF NOT EXISTS plants_per_unit INTEGER DEFAULT 1")
        cur.execute("ALTER TABLE plants ADD COLUMN IF NOT EXISTS container_stock INTEGER DEFAULT 0")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS seeds (
                id                  SERIAL PRIMARY KEY,
                name                VARCHAR(150) NOT NULL,
                variety             VARCHAR(100) DEFAULT '',
                supplier            VARCHAR(150) DEFAULT '',
                quantity_grams      NUMERIC(10,2) DEFAULT 0,
                quantity_packets    INTEGER DEFAULT 0,
                grams_per_packet    NUMERIC(10,2) DEFAULT 0,
                unit_price_gram     NUMERIC(10,2) DEFAULT 0,
                unit_price_packet   NUMERIC(10,2) DEFAULT 0,
                low_stock_grams     NUMERIC(10,2) DEFAULT 100,
                germination_rate    NUMERIC(5,2) DEFAULT 0,
                notes               TEXT DEFAULT '',
                created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS containers (
                id              SERIAL PRIMARY KEY,
                name            VARCHAR(150) NOT NULL,
                container_type  VARCHAR(50) DEFAULT 'Tray',
                capacity        INTEGER DEFAULT 0,
                stock_qty       INTEGER DEFAULT 0,
                unit_cost       NUMERIC(10,2) DEFAULT 0,
                notes           TEXT DEFAULT '',
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


def _create_production_tables():
    """Stage 2: Production tables (Depends on seeds)."""
    with get_connection() as conn:
        cur = conn.cursor()

        # ── Production Lots ─────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS production_lots (
                id              SERIAL PRIMARY KEY,
                lot_number      VARCHAR(30) UNIQUE NOT NULL,
                plant_name      VARCHAR(150) NOT NULL,
                category        VARCHAR(100) DEFAULT '',
                seed_id         INTEGER REFERENCES seeds(id) ON DELETE SET NULL,
                quantity        INTEGER NOT NULL DEFAULT 0,
                tray_count      INTEGER DEFAULT 0,
                plants_per_tray INTEGER DEFAULT 50,
                tray_type       VARCHAR(50) DEFAULT '',
                seed_quantity   INTEGER DEFAULT 0,
                location        VARCHAR(100) DEFAULT '',
                created_by      VARCHAR(100) DEFAULT '',
                notes           TEXT DEFAULT '',
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Safe column additions if table already existed
        cur.execute("ALTER TABLE production_lots ADD COLUMN IF NOT EXISTS category VARCHAR(100) DEFAULT ''")
        cur.execute("ALTER TABLE production_lots ADD COLUMN IF NOT EXISTS tray_type VARCHAR(50) DEFAULT ''")
        cur.execute("ALTER TABLE production_lots ADD COLUMN IF NOT EXISTS seed_quantity INTEGER DEFAULT 0")
        cur.execute("ALTER TABLE production_lots ADD COLUMN IF NOT EXISTS location VARCHAR(100) DEFAULT ''")

        # ── Production Stages ─────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS production_stages (
                id              SERIAL PRIMARY KEY,
                lot_id          INTEGER NOT NULL REFERENCES production_lots(id) ON DELETE CASCADE,
                stage           VARCHAR(30) NOT NULL,
                stage_date      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                quantity_in     INTEGER DEFAULT 0,
                quantity_out    INTEGER DEFAULT 0,
                quantity_scrap  INTEGER DEFAULT 0,
                tray_count      INTEGER DEFAULT 0,
                location        VARCHAR(100) DEFAULT '',
                notes           TEXT DEFAULT '',
                price           FLOAT DEFAULT 0.0,
                done_by         VARCHAR(100) DEFAULT '',
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("ALTER TABLE production_stages ADD COLUMN IF NOT EXISTS price FLOAT DEFAULT 0.0")

        # ── Production Scrap ─────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS production_scrap (
                id          SERIAL PRIMARY KEY,
                lot_id      INTEGER REFERENCES production_lots(id) ON DELETE CASCADE,
                stage_id    INTEGER REFERENCES production_stages(id) ON DELETE SET NULL,
                quantity    INTEGER NOT NULL DEFAULT 0,
                reason      VARCHAR(200) DEFAULT '',
                scrap_date  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes       TEXT DEFAULT '',
                recorded_by VARCHAR(100) DEFAULT ''
            )
        """)


def _create_transaction_tables():
    """Stage 3: Orders and Invoices (Depends on customers and production_lots)."""
    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id               SERIAL PRIMARY KEY,
                customer_id      INTEGER REFERENCES customers(id),
                order_date       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status           VARCHAR(30) DEFAULT 'Pending',
                notes            TEXT,
                total_amount     NUMERIC(10,2) DEFAULT 0,
                
                delivery_status  VARCHAR(30) DEFAULT 'Pending',
                delivery_notes   TEXT DEFAULT '',
                failure_reason   TEXT DEFAULT '',
                delivered_at     TIMESTAMP,
                
                packed_by        VARCHAR(150) DEFAULT '',
                dispatched_by    VARCHAR(150) DEFAULT '',
                received_by      VARCHAR(150) DEFAULT ''
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                id                SERIAL PRIMARY KEY,
                order_id          INTEGER REFERENCES orders(id) ON DELETE CASCADE,
                production_lot_id INTEGER REFERENCES production_lots(id) ON DELETE RESTRICT, 
                quantity          INTEGER NOT NULL,
                unit_price        NUMERIC(10,2) NOT NULL,
                subtotal          NUMERIC(10,2) GENERATED ALWAYS AS (quantity * unit_price) STORED
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id           SERIAL PRIMARY KEY,
                order_id     INTEGER REFERENCES orders(id),
                invoice_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                due_date     DATE,
                paid         BOOLEAN DEFAULT FALSE,
                paid_date    TIMESTAMP,
                notes        TEXT,
                discount_amount NUMERIC(10,2) DEFAULT 0,
                price_override_notes TEXT DEFAULT ''
            )
        """)
        cur.execute("ALTER TABLE invoices ADD COLUMN IF NOT EXISTS discount_amount NUMERIC(10,2) DEFAULT 0")
        cur.execute("ALTER TABLE invoices ADD COLUMN IF NOT EXISTS price_override_notes TEXT DEFAULT ''")


def _create_otp_table():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS otp_sessions (
                id          SERIAL PRIMARY KEY,
                phone       VARCHAR(20) NOT NULL,
                otp_code    VARCHAR(10) NOT NULL,
                purpose     VARCHAR(30) DEFAULT 'reset_password',
                used        BOOLEAN DEFAULT FALSE,
                expires_at  TIMESTAMP NOT NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


def _seed_default_owner():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM app_users WHERE role='owner' LIMIT 1")
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO app_users (username, password_hash, role, full_name)
                VALUES (%s, %s, 'owner', 'Business Owner')
            """, ("deepak1", hash_password("deepak")))


def get_table_columns(table_name: str,
                      exclude: list = None,
                      prettify: bool = True) -> list:
    """
    Returns table columns from PostgreSQL.

    Args:
        table_name : database table name
        exclude    : columns to ignore
        prettify   : convert snake_case to Title Case

    Example:
        get_table_columns("plants")
    """

    exclude = exclude or []

    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position
        """, (table_name,))

        columns = []

        for row in cur.fetchall():
            col = row[0]

            if col in exclude:
                continue

            if prettify:
                col = col.replace("_", " ").title()

            columns.append(col)

        return columns