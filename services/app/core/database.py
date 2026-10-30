"""TinyDB initialization for the HealthCore Supplier Directory and auth,
plus SQLModel engine/session for Supabase inventory.
"""
from collections.abc import Generator
from functools import lru_cache
"""TinyDB initialization for HealthCore suppliers, auth, and incidents."""
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

    # Pin psycopg2 explicitly: SQLAlchemy >= 2.1 defaults postgresql://
    # to the psycopg (v3) driver, which is not installed here.
    return f"postgresql+psycopg2://{user}:{quote_plus(password)}@{host}:{port}/{name}"


@lru_cache(maxsize=1)
def get_engine():
    return create_engine(
        _resolve_database_url(),
        echo=False,
        pool_pre_ping=True,
    )


def init_inventory_db() -> None:
    """Create inventory, telemetry, and RFP intake tables if they do not exist."""
    from services.app.models import inventory as _inventory  # noqa: F401
    from services.app.models import telemetry as _telemetry  # noqa: F401
    from services.app.models import task as _task  # noqa: F401
    from services.app.models import rfp as _rfp  # noqa: F401

    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    # Part 2 columns (create_all does not ALTER existing tables).
    _ensure_rfp_part2_columns(engine)


def _ensure_rfp_part2_columns(engine) -> None:
    """Idempotent ADD COLUMN for Part 2/3 fields on existing DBs."""
    statements = (
        "ALTER TABLE rfp_tickets ADD COLUMN IF NOT EXISTS ready_for_part3 BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE rfp_tickets ADD COLUMN IF NOT EXISTS part2_handoff_payload JSONB NOT NULL DEFAULT '{}'::jsonb",
        "ALTER TABLE rfp_tickets ADD COLUMN IF NOT EXISTS trace_events JSONB NOT NULL DEFAULT '[]'::jsonb",
        "ALTER TABLE rfp_tickets ADD COLUMN IF NOT EXISTS final_document_id INTEGER",
        "ALTER TABLE rfp_department_sections ADD COLUMN IF NOT EXISTS iteration_count INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE rfp_department_sections ADD COLUMN IF NOT EXISTS needs_human_review BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE rfp_department_sections ADD COLUMN IF NOT EXISTS approval_round INTEGER NOT NULL DEFAULT 0",
    )
    try:
        with engine.begin() as conn:
            for stmt in statements:
                conn.exec_driver_sql(stmt)
    except Exception:
        # Non-Postgres or permissions — create_all path for fresh DBs is enough.
        pass


def get_db() -> Generator[Session, None, None]:
    """Yield a per-request SQLModel session (no global session)."""
    with Session(get_engine()) as session:
        yield session
password_reset_tokens_table = auth_db.table("password_reset_tokens")
# Machine (service) identities for internal tool callers — client-credentials.
service_clients_table = auth_db.table("service_clients")

INCIDENTS_DB_PATH = DATA_DIR / "process" / "incidents" / "incidents.json"
INCIDENTS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

incidents_db = TinyDB(INCIDENTS_DB_PATH)
incidents_table = incidents_db.table("incidents")
