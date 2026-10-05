import math

from quart import Quart, g, jsonify, request
from quart.helpers import make_response

from app.db import SessionLocal
from app.models import Basin, SteamBand
from app.repositories import BasinRepo, SteamBandRepo, UserRepo
from app.security import make_token, parse_token, verify_password
from app.services import (
    RuleError,
    assert_band_bounds,
    assert_can_set_status,
    assert_opening_in_band,
    latest_temp,
)

app = Quart(__name__)


def _bearer() -> str | None:
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[7:]
    return None


@app.before_request
async def load_user():
    g.user = None
    token = _bearer()
    if not token:
        return
    username = parse_token(token)
    if not username:
        return
    async with SessionLocal() as session:
        g.user = await UserRepo(session).by_username(username)


def require_user():
    if g.user is None:
        return jsonify({"detail": "未登录"}), 401
    return None


def require_admin():
    denied = require_user()
    if denied:
        return denied
    if g.user.role != "admin":
        return jsonify({"detail": "仅管理员可改开度带"}), 403
    return None


@app.route("/api/health")
async def health():
    return {"status": "ok", "service": "SilkReel"}


@app.route("/api/auth/login", methods=["POST"])
async def login():
    body = await request.get_json(force=True)
    username = (body or {}).get("username", "")
    password = (body or {}).get("password", "")
    async with SessionLocal() as session:
        user = await UserRepo(session).by_username(username)
        if user is None or not verify_password(password, user.password_hash):
            return jsonify({"detail": "用户名或密码错误"}), 401
        return {
            "access_token": make_token(user.username),
            "user": {"username": user.username, "role": user.role},
        }


@app.route("/api/auth/me")
async def me():
    denied = require_user()
    if denied:
        return denied
    return {"username": g.user.username, "role": g.user.role}


def _basin_json(basin: Basin) -> dict:
    return {
        "id": basin.id,
        "code": basin.code,
        "status": basin.status,
        "ringIndex": basin.ring_index,
        "latestTempC": latest_temp(basin),
        "readingCount": len(basin.readings or []),
    }


@app.route("/api/board")
async def board():
    denied = require_user()
    if denied:
        return denied
    async with SessionLocal() as session:
        mill = await BasinRepo(session).board()
        if mill is None:
            return jsonify({"detail": "尚无缫丝坞"}), 404
        basins = sorted(mill.basins, key=lambda b: b.ring_index)
        return {
            "filature": mill.name,
            "riverside": mill.riverside,
            "basins": [_basin_json(b) for b in basins],
        }


@app.route("/api/basins/<int:basin_id>/readings", methods=["POST"])
async def add_reading(basin_id: int):
    denied = require_user()
    if denied:
        return denied
    body = await request.get_json(force=True)
    try:
        temp = float((body or {}).get("waterTempC"))
    except (TypeError, ValueError):
        return jsonify({"detail": "汤温必须是数字"}), 400
    try:
        opening = float((body or {}).get("steamPct"))
    except (TypeError, ValueError):
        return jsonify({"detail": "蒸汽开度必须是数字"}), 400
    if not (math.isfinite(temp) and math.isfinite(opening)):
        return jsonify({"detail": "汤温与蒸汽开度必须是有限数字"}), 400
    async with SessionLocal() as session:
        repo = BasinRepo(session)
        basin = await repo.get(basin_id)
        if basin is None:
            return jsonify({"detail": "盆不存在"}), 404
        # 先读现行开度带验开度，出带整笔拒绝——不得先插入汤温再改。
        band = await SteamBandRepo(session).current(basin.filature_id)
        try:
            assert_opening_in_band(band, opening)
        except RuleError as exc:
            return jsonify({"detail": str(exc)}), 400
        await repo.add_reading(basin, temp, opening, g.user.username)
        basin = await repo.get(basin_id)
        return _basin_json(basin)


@app.route("/api/basins/<int:basin_id>/status", methods=["POST"])
async def set_status(basin_id: int):
    denied = require_user()
    if denied:
        return denied
    body = await request.get_json(force=True)
    status = (body or {}).get("status", "")
    async with SessionLocal() as session:
        repo = BasinRepo(session)
        basin = await repo.get(basin_id)
        if basin is None:
            return jsonify({"detail": "盆不存在"}), 404
        try:
            assert_can_set_status(basin, status)
        except RuleError as exc:
            return jsonify({"detail": str(exc)}), 400
        await repo.save_status(basin, status)
        basin = await repo.get(basin_id)
        return _basin_json(basin)


def _band_json(band: SteamBand, filature: str) -> dict:
    return {
        "filature": filature,
        "filatureId": band.filature_id,
        "lowerPct": band.lower_pct,
        "upperPct": band.upper_pct,
        "updatedBy": band.updated_by,
        "updatedAt": band.updated_at.isoformat() if band.updated_at else None,
    }


@app.route("/api/steam-band")
async def get_steam_band():
    denied = require_user()
    if denied:
        return denied
    async with SessionLocal() as session:
        mill = await BasinRepo(session).board()
        if mill is None:
            return jsonify({"detail": "尚无缫丝坞"}), 404
        band = await SteamBandRepo(session).current(mill.id)
        if band is None:
            return jsonify({"detail": "该坞尚无蒸汽开度带"}), 404
        return _band_json(band, mill.name)


@app.route("/api/steam-band", methods=["PUT"])
async def put_steam_band():
    denied = require_admin()
    if denied:
        return denied
    body = await request.get_json(force=True)
    try:
        lower = float((body or {}).get("lowerPct"))
        upper = float((body or {}).get("upperPct"))
    except (TypeError, ValueError):
        return jsonify({"detail": "上下限必须是数字"}), 400
    if not (math.isfinite(lower) and math.isfinite(upper)):
        return jsonify({"detail": "上下限必须是有限数字"}), 400
    try:
        assert_band_bounds(lower, upper)
    except RuleError as exc:
        return jsonify({"detail": str(exc)}), 400
    async with SessionLocal() as session:
        mill = await BasinRepo(session).board()
        if mill is None:
            return jsonify({"detail": "尚无缫丝坞"}), 404
        band = await SteamBandRepo(session).upsert(
            mill.id, lower, upper, g.user.username
        )
        return _band_json(band, mill.name)
