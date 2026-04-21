import os
import logging
from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)

# ─── DATABASE URL ─────────────────────────────────────────────────────────────
# Priority:
#   1. DATABASE_URL env var  (Railway / Render / Heroku set this automatically)
#   2. Individual PG env vars (manual hosting)
#   3. SQLite fallback        (local dev only — never use in production)
# Force read from Railway environment — never from .env file
import os
_db_url = os.environ.get("DATABASE_URL", "")
print(f"ENV CHECK: DATABASE_URL={'SET' if _db_url else 'NOT SET'}, value starts with: {_db_url[:20] if _db_url else 'EMPTY'}")

# Railway/Heroku Postgres URLs sometimes start with "postgres://" — SQLAlchemy
# requires "postgresql+psycopg2://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)

# Build from individual parts if DATABASE_URL not set
if not DATABASE_URL:
    PG_HOST     = os.getenv("PGHOST",     "")
    PG_PORT     = os.getenv("PGPORT",     "5432")
    PG_USER     = os.getenv("PGUSER",     "")
    PG_PASSWORD = os.getenv("PGPASSWORD", "")
    PG_DB       = os.getenv("PGDATABASE", "trading_bot")

    if all([PG_HOST, PG_USER, PG_PASSWORD]):
        DATABASE_URL = (
            f"postgresql+psycopg2://{PG_USER}:{PG_PASSWORD}"
            f"@{PG_HOST}:{PG_PORT}/{PG_DB}"
        )
    else:
        DATABASE_URL = "sqlite:///./trading_bot.db"
        logger.warning(
            "⚠️  No DATABASE_URL or PG* variables found — "
            "falling back to SQLite (NOT suitable for production)."
        )

IS_SQLITE = DATABASE_URL.startswith("sqlite")

# ─── ENGINE ───────────────────────────────────────────────────────────────────
if IS_SQLITE:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=10,          # persistent connections kept open
        max_overflow=20,       # extra connections allowed under burst load
        pool_pre_ping=True,    # auto-reconnect on stale connections
        pool_recycle=1800,     # recycle connections every 30 min
        connect_args={
            "connect_timeout": 10,
            "options": "-c timezone=utc",
        },
    )
    # Log which DB we connected to (redact password)
    safe_url = DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL
    logger.info(f"✅ PostgreSQL connected → {safe_url}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ─── HEALTH CHECK ─────────────────────────────────────────────────────────────
def check_db_connection() -> bool:
    """Returns True if the DB is reachable. Used by /api/health."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"DB health check failed: {e}")
        return False


# ─── FASTAPI DEPENDENCY ───────────────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
