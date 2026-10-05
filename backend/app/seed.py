from datetime import timedelta

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Basin, BathReading, Filature, SteamBand, User, utcnow
from app.security import hash_password

SEED_BAND_MIN = 20.0
SEED_BAND_MAX = 40.0


async def seed_demo() -> None:
    async with SessionLocal() as session:
        existing = await session.execute(select(User).where(User.username == "admin"))
        admin = existing.scalar_one_or_none()
        if admin is None:
            admin = User(username="admin", password_hash=hash_password("123456"), role="admin")
            session.add(admin)
        else:
            admin.password_hash = hash_password("123456")
            admin.role = "admin"

        existing_w = await session.execute(select(User).where(User.username == "worker"))
        worker = existing_w.scalar_one_or_none()
        if worker is None:
            session.add(User(username="worker", password_hash=hash_password("123456"), role="worker"))
        else:
            worker.password_hash = hash_password("123456")
            worker.role = "worker"

        mill = (await session.execute(select(Filature))).scalars().first()
        if mill:
            await _ensure_seed_band(session, mill.id)
            await session.commit()
            return

        mill = Filature(name="江口缫丝坞", riverside="东津渡")
        session.add(mill)
        await session.flush()
        now = utcnow()
        specs = [
            ("甲-1", Basin.STATUS_REELING, 40.5, 0),
            ("甲-2", Basin.STATUS_SOAKING, None, 1),
            ("乙-1", Basin.STATUS_REELED, 39.2, 2),
            ("乙-2", Basin.STATUS_REELING, 36.0, 3),
            ("丙-1", Basin.STATUS_SOAKING, None, 4),
            ("丙-2", Basin.STATUS_REELED, 41.0, 5),
        ]
        for code, status, temp, idx in specs:
            basin = Basin(filature_id=mill.id, code=code, status=status, ring_index=idx)
            session.add(basin)
            await session.flush()
            if temp is not None:
                session.add(
                    BathReading(
                        basin_id=basin.id,
                        water_temp_c=temp,
                        operator="worker",
                        taken_at=now - timedelta(hours=2),
                    )
                )
        await _ensure_seed_band(session, mill.id)
        await session.commit()


async def _ensure_seed_band(session, filature_id: int) -> None:
    """老库补建现行开度带 20～40；主管已设置过则不覆盖。"""
    existing = await session.execute(
        select(SteamBand).where(SteamBand.filature_id == filature_id)
    )
    if existing.scalar_one_or_none() is not None:
        return
    session.add(
        SteamBand(
            filature_id=filature_id,
            min_pct=SEED_BAND_MIN,
            max_pct=SEED_BAND_MAX,
            updated_by="admin",
        )
    )
