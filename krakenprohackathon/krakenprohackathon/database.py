import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)

# Read DATABASE_URL directly from environment
DATABASE_URL = os.environ.get("DATABASE_URL", "")

print(f"DEBUG: DATABASE_URL starts with: {DATABASE_URL[:30] if DATABASE_URL else 'EMPTY'}")

# Fix Railway/Heroku postgres:// URLs
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+psycopg2" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

# Fallback to individual PG vars
if not DATABASE_URL:
    PG_HOST     = os.environ.get("PGHOST",     "")
    PG_PORT     = os.environ.get("PGPORT",     "5432")
    PG_USER     = os.environ.get("PGUSER",     "")
    PG_PASSWORD = os.environ.get("PGPASSWORD", "")
    PG_DB       = os.environ.get("PGDATABASE", "trading_bot")

    if all([PG_HOST, PG_USER, PG_PASSWORD]):
        DATABASE_URL = f"postgresql+psycopg2://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}"
    else:
        DATABASE_URL = "sqlite:///./trading_bot.db"
        logger.warning("⚠️  No DATABASE_URL or PG* variables found — falling back to SQLite")

IS_SQLITE = DATABASE_URL.startswith("sqlite")

if IS_SQLITE:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=1800,
        connect_args={"connect_timeout": 10, "options": "-c timezone=utc"},
    )
    safe_url = DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL
    logger.info(f"✅ PostgreSQL connected → {safe_url}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def check_db_connection() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"DB health check failed: {e}")
        return False

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()# cache bust Tue, Apr 21, 2026  6:47:42 PM
