import os
import socket
from urllib.parse import urlparse
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from app.core.config import settings

def is_postgres_available(host: str = "localhost", port: int = 5432, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

# Determine database URL: check if postgres is reachable on port 5432
sqlite_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../doc_intelligence.db"))
default_sqlite_url = f"sqlite+aiosqlite:///{sqlite_path}"

if "postgresql" in settings.DATABASE_URL:
    try:
        parsed = urlparse(settings.DATABASE_URL.replace("postgresql+asyncpg://", "http://"))
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
        if is_postgres_available(host, port):
            db_url = settings.DATABASE_URL
            is_sqlite = False
        else:
            print(f"[!] PostgreSQL not detected on {host}:{port}. Instant auto-fallback to local SQLite ({sqlite_path})")
            db_url = default_sqlite_url
            is_sqlite = True
    except Exception:
        db_url = default_sqlite_url
        is_sqlite = True
else:
    db_url = settings.DATABASE_URL
    is_sqlite = "sqlite" in db_url

connect_args = {"check_same_thread": False} if is_sqlite else {"timeout": 2.0}

engine = create_async_engine(
    db_url,
    echo=False,
    future=True,
    connect_args=connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    """Initialize database tables instantly on startup."""
    global engine, AsyncSessionLocal, is_sqlite
    async with engine.begin() as conn:
        if not is_sqlite:
            try:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            except Exception:
                pass
        await conn.run_sync(Base.metadata.create_all)
    print(f"[+] Database ready: {'SQLite (doc_intelligence.db)' if is_sqlite else 'PostgreSQL (pgvector)'}")
