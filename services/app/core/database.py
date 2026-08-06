"""TinyDB initialization for the HealthCore Supplier Directory.

Stores the database file inside data/ so it persists across server restarts.
"""
from pathlib import Path

from tinydb import TinyDB

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "process" / "suppliers" / "suppliers.json"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

db = TinyDB(DB_PATH)
suppliers_table = db.table("suppliers")
