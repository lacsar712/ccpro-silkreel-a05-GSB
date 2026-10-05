"""缫丝盆门槛：标成已缫完须最近一次汤温落在 38～42℃。

登记汤温另有一道门槛：该坞现行蒸汽开度必须落在开度带
下限与上限之间（含边界），出带则整笔拒绝。开度带只管
登记汤温，顶不掉已缫完的 38～42℃ 汤温带。"""

from app.models import Basin, SteamBand

MIN_TEMP = 38.0
MAX_TEMP = 42.0


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


def assert_band_bounds(lower_pct: float, upper_pct: float) -> None:
    if lower_pct > upper_pct:
        raise RuleError("开度带下限不得大于上限")


def assert_opening_in_band(band: SteamBand | None, opening_pct: float) -> None:
    if band is None:
        raise RuleError("该坞尚无蒸汽开度带，不能登记汤温")
    if opening_pct < band.lower_pct or opening_pct > band.upper_pct:
        raise RuleError(
            f"蒸汽开度 {opening_pct:g}% 出带（现行带 "
            f"{band.lower_pct:g}%～{band.upper_pct:g}%），整笔拒绝"
        )
