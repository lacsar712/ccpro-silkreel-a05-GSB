from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Basin, BathReading, Filature, SteamBand, User, utcnow


class UserRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def by_username(self, username: str) -> User | None:
        result = await self.session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()


class BasinRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def board(self) -> Filature | None:
        result = await self.session.execute(
            select(Filature).options(
                selectinload(Filature.basins).selectinload(Basin.readings)
            )
        )
        return result.scalars().first()

    async def get(self, basin_id: int) -> Basin | None:
        result = await self.session.execute(
            select(Basin)
            .options(selectinload(Basin.readings))
            .where(Basin.id == basin_id)
        )
        return result.scalar_one_or_none()

    async def add_reading(
        self, basin: Basin, temp_c: float, steam_pct: float, operator: str
    ) -> BathReading:
        row = BathReading(
            basin=basin, water_temp_c=temp_c, steam_pct=steam_pct, operator=operator
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def save_status(self, basin: Basin, status: str) -> None:
        basin.status = status
        await self.session.commit()


class SteamBandRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def current(self, filature_id: int) -> SteamBand | None:
        result = await self.session.execute(
            select(SteamBand).where(SteamBand.filature_id == filature_id)
        )
        return result.scalar_one_or_none()

    async def upsert(
        self, filature_id: int, lower_pct: float, upper_pct: float, username: str
    ) -> SteamBand:
        # 同一坞现行带最多一条：ON CONFLICT 原子覆盖，两名主管交叉提交也只留一版。
        stmt = pg_insert(SteamBand).values(
            filature_id=filature_id,
            lower_pct=lower_pct,
            upper_pct=upper_pct,
            updated_by=username,
            updated_at=utcnow(),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[SteamBand.filature_id],
            set_={
                "lower_pct": lower_pct,
                "upper_pct": upper_pct,
                "updated_by": username,
                "updated_at": utcnow(),
            },
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return await self.current(filature_id)
