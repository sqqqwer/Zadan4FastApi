from sqlalchemy import URL
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)

from .config import get_settings

DATABASE_URL = URL.create(
    drivername="postgresql+asyncpg",
    username=get_settings().postgres_user,
    password=get_settings().postgres_password.get_secret_value(),
    host=get_settings().db_host,
    port=get_settings().db_port,
    database=get_settings().postgres_db,
)

async_engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
async_session_factory = async_sessionmaker(async_engine, expire_on_commit=False)
