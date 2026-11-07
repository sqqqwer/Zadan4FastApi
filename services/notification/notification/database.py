from sqlalchemy import URL
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from .config import get_settings

settings = get_settings()

DATABASE_URL = URL.create(
    drivername="postgresql+asyncpg",
    username=settings.postgres_user,
    password=settings.postgres_password.get_secret_value(),
    host=settings.db_host,
    port=settings.db_port,
    database=settings.postgres_db,
)

async_engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
async_session_factory = async_sessionmaker(async_engine, expire_on_commit=False)
