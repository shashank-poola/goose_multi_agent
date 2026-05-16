from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import event

from backend.core.config import settings

engine = create_async_engine(
    settings.database_url,
    connect_args={"check_same_thread": False, "timeout": 30},
    echo=False,
    pool_pre_ping=True,
)

# Production SQLite pragmas applied on every new connection
@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, _record):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")       # concurrent reads + writes
    cur.execute("PRAGMA foreign_keys=ON")         # enforce FK constraints
    cur.execute("PRAGMA synchronous=NORMAL")      # safe + faster than FULL
    cur.execute("PRAGMA cache_size=-65536")       # 64 MB page cache
    cur.execute("PRAGMA temp_store=MEMORY")       # temp tables in RAM
    cur.execute("PRAGMA mmap_size=268435456")     # 256 MB memory-mapped I/O
    cur.close()


AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncSession:  # FastAPI dependency
    async with AsyncSessionLocal() as session:
        yield session


async def create_tables() -> None:
    from backend.db.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
