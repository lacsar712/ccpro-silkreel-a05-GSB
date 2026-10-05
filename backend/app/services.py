"""缫丝盆门槛。

- 标成已缫完须最近一次汤温落在 38～42℃（只认汤温带）。
- 登记汤温时该坞现行蒸汽开度必须落在开度带 [下限, 上限]（含边界），
  出带整笔拒绝，不得先写入汤温。开度带不顶掉汤温带。
"""

from app.models import Basin, SteamBand

MIN_TEMP = 38.0
MAX_TEMP = 42.0

MIN_OPENING = 0.0
MAX_OPENING = 100.0


class RuleError(ValueError):
    pass


def latest_temp(basin: Basin) -> float | None:
    if not basin.readings:
        return None
    latest = max(basin.readings, key=lambda r: r.taken_at)
    return latest.water_temp_c


def assert_can_set_status(basin: Basin, new_status: str) -> None:
    allowed = {Basin.STATUS_SOAKING, Basin.STATUS_REELING, Basin.STATUS_REELED}
    if new_status not in allowed:
        raise RuleError(f"无效状态：{new_status}")
    if new_status != Basin.STATUS_REELED:
        return
    temp = latest_temp(basin)
    if temp is None:
        raise RuleError("该盆尚无汤温记录，不能标已缫完")
    if temp < MIN_TEMP or temp > MAX_TEMP:
        raise RuleError(
            f"最近汤温 {temp}℃ 不在 {MIN_TEMP:.0f}～{MAX_TEMP:.0f}℃，不能标已缫完"
        )


def assert_band_bounds(min_pct: float, max_pct: float) -> None:
    if not (MIN_OPENING <= min_pct <= MAX_OPENING) or not (
        MIN_OPENING <= max_pct <= MAX_OPENING
    ):
        raise RuleError(
            f"开度百分必须在 {MIN_OPENING:g}～{MAX_OPENING:g} 之间"
        )
    if min_pct > max_pct:
        raise RuleError(
            f"下限 {min_pct:g}% 不得大于上限 {max_pct:g}%"
        )


def assert_opening_in_band(band: SteamBand | None, steam_pct: float) -> None:
    if band is None:
        raise RuleError("该坞尚未设置蒸汽开度带，不能登记汤温")
    if steam_pct < band.min_pct or steam_pct > band.max_pct:
        raise RuleError(
            f"蒸汽开度 {steam_pct:g}% 超出该坞现行开度带 "
            f"{band.min_pct:g}～{band.max_pct:g}%（含边界），整笔拒绝"
        )
