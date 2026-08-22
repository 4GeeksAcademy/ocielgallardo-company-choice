"""TinyDB initialization for the HealthCore Supplier Directory and auth,
plus SQLModel engine/session for Supabase inventory.
"""
from collections.abc import Generator
from functools import lru_cache
from pathlib import Path
import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, create_engine
from tinydb import TinyDB

_REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_REPO_ROOT / ".env")

DATA_DIR = _REPO_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "process" / "suppliers" / "suppliers.json"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

db = TinyDB(DB_PATH)
suppliers_table = db.table("suppliers")

AUTH_DB_PATH = DATA_DIR / "process" / "auth" / "auth.json"
AUTH_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

auth_db = TinyDB(AUTH_DB_PATH)
users_table = auth_db.table("users")
profiles_table = auth_db.table("profiles")


def is_inventory_db_configured() -> bool:
    """Return True when DATABASE_URL or discrete SUPABASE_DB_* vars are set."""
    if os.getenv("DATABASE_URL"):
        return True
    return all(
        os.getenv(key)
        for key in ("SUPABASE_DB_HOST", "SUPABASE_DB_USER", "SUPABASE_DB_PASSWORD")
    )


def _resolve_database_url() -> str:
    if url := os.getenv("DATABASE_URL"):
        return url

    host = os.getenv("SUPABASE_DB_HOST")
    user = os.getenv("SUPABASE_DB_USER")
    password = os.getenv("SUPABASE_DB_PASSWORD")
    port = os.getenv("SUPABASE_DB_PORT", "6543")
    name = os.getenv("SUPABASE_DB_NAME", "postgres")

    if not all([host, user, password]):
        raise RuntimeError(
            "Database not configured. Set DATABASE_URL or "
            "SUPABASE_DB_HOST, SUPABASE_DB_USER, and SUPABASE_DB_PASSWORD in .env"
        )

    return f"postgresql://{user}:{quote_plus(password)}@{host}:{port}/{name}"


@lru_cache(maxsize=1)
def get_engine():
    return create_engine(
        _resolve_database_url(),
        echo=False,
        pool_pre_ping=True,
    )


def init_inventory_db() -> None:
    """Create inventory tables in Supabase if they do not exist."""
    from services.app.models import inventory as _inventory  # noqa: F401

    SQLModel.metadata.create_all(get_engine())


def get_db() -> Generator[Session, None, None]:
    """Yield a per-request SQLModel session (no global session)."""
    with Session(get_engine()) as session:
        yield session
