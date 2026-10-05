from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import DATABASE_URL
from app.models import Base

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # 旧库补列（create_all 不会 ALTER 已存在的表），按方言安全判断。
        await conn.run_sync(_add_steam_pct_if_missing)


def _add_steam_pct_if_missing(sync_conn) -> None:
    from sqlalchemy import inspect

    cols = {c["name"] for c in inspect(sync_conn).get_columns("bath_readings")}
    if "steam_pct" not in cols:
        sync_conn.exec_driver_sql(
            "ALTER TABLE bath_readings ADD COLUMN steam_pct FLOAT"
        )


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
