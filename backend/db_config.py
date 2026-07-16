"""
backend/db_config.py
====================
Saves and loads database connection settings to a local config file.
Each client machine has its own db_config.json pointing to the server IP.
The server machine uses 'localhost'.
"""

import json
import os

# Config file stored next to the app
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db_config.json")

DEFAULT_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "database": "nursery_erp",
    "user":     "postgres",
    "password": "",
    "app_name": "Hind Agro Products ERP",
}


def load_config() -> dict:
    """Load config from file, fall back to defaults if missing."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                saved = json.load(f)
            cfg = DEFAULT_CONFIG.copy()
            cfg.update(saved)
            return cfg
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(cfg: dict):
    """Save config to file."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def get_db_config() -> dict:
    """Returns only the psycopg2-compatible keys."""
    cfg = load_config()
    return {
        "host":     cfg["host"],
        "port":     int(cfg["port"]),
        "database": cfg["database"],
        "user":     cfg["user"],
        "password": cfg["password"],
    }


def is_configured() -> bool:
    """Returns True if a config file exists (user has set up connection)."""
    return os.path.exists(CONFIG_FILE)


def get_display_info() -> str:
    """Returns a short human-readable connection string."""
    cfg = load_config()
    return f"{cfg['host']}:{cfg['port']} / {cfg['database']}"
