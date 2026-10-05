from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Basin, BathReading, Filature, SteamBand, User


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
            select(Filature)
            .options(
                selectinload(Filature.basins).selectinload(Basin.readings),
                selectinload(Filature.steam_band),
            )
        )
        return result.scalars().first()

    async def get(self, basin_id: int) -> Basin | None:
        result = await self.session.execute(
            select(Basin)
            .options(
                selectinload(Basin.readings),
                selectinload(Basin.filature).selectinload(Filature.steam_band),
            )
            .where(Basin.id == basin_id)
        )
        return result.scalar_one_or_none()

    async def lock_current_band(self, filature_id: int) -> SteamBand | None:
        """在当前事务内锁定该坞现行开度带（唯一一行）。"""
        result = await self.session.execute(
            select(SteamBand)
            .where(SteamBand.filature_id == filature_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def add_reading(
        self,
        basin: Basin,
        temp_c: float,
        operator: str,
        steam_pct: float | None = None,
    ) -> BathReading:
        row = BathReading(
            basin=basin,
            water_temp_c=temp_c,
            steam_pct=steam_pct,
            operator=operator,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def save_status(self, basin: Basin, status: str) -> None:
        basin.status = status
        await self.session.commit()

    async def get_filature(self, filature_id: int) -> Filature | None:
        result = await self.session.execute(
            select(Filature)
            .options(selectinload(Filature.steam_band))
            .where(Filature.id == filature_id)
        )
        return result.scalar_one_or_none()

    async def list_bands(self) -> list[SteamBand]:
        result = await self.session.execute(
            select(SteamBand).options(selectinload(SteamBand.filature))
        )
        return list(result.scalars().all())

    async def upsert_steam_band(
        self,
        filature_id: int,
        min_pct: float,
        max_pct: float,
        username: str,
    ) -> SteamBand:
        """同一坞只保留一版：命中则更新，否则插入；并发首插靠唯一约束决胜。"""
        band = await self._fetch_band(filature_id)
        if band is not None:
            band.min_pct = min_pct
            band.max_pct = max_pct
            band.updated_by = username
            await self.session.commit()
            await self.session.refresh(band)
            return band

        band = SteamBand(
            filature_id=filature_id,
            min_pct=min_pct,
            max_pct=max_pct,
            updated_by=username,
        )
        self.session.add(band)
        try:
            await self.session.commit()
        except IntegrityError:
            # 两名主管并发首插：唯一约束只放行一条，落败方改为更新留下的那版。
            await self.session.rollback()
            band = await self._fetch_band(filature_id, required=True)
            band.min_pct = min_pct
            band.max_pct = max_pct
            band.updated_by = username
            await self.session.commit()
        await self.session.refresh(band)
        return band

    async def get_band(self, filature_id: int) -> SteamBand | None:
        result = await self.session.execute(
            select(SteamBand)
            .options(selectinload(SteamBand.filature))
            .where(SteamBand.filature_id == filature_id)
        )
        return result.scalar_one_or_none()

    async def _fetch_band(
        self, filature_id: int, required: bool = False
    ) -> SteamBand | None:
        result = await self.session.execute(
            select(SteamBand).where(SteamBand.filature_id == filature_id)
        )
        if required:
            return result.scalar_one()
        return result.scalar_one_or_none()
