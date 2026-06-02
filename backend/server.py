"""BAIS Summary Geospasika - FastAPI backend (single-file)."""
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import logging
import secrets
from datetime import datetime, timezone, timedelta, time as dtime, date as ddate
from typing import Optional, List, Literal, Dict, Any

import bcrypt
import jwt
from bson import ObjectId
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, Body
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field, field_validator
from starlette.middleware.cors import CORSMiddleware

from pdf_generator import build_summary_pdf
from ai_summary import generate_ai_summary

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = logging.getLogger("bais")

# ---------- Mongo ----------
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

JWT_ALGORITHM = "HS256"
WIB = timezone(timedelta(hours=7))
# Reporting window cutoff (WIB). Data entered BEFORE this hour belongs to the
# PREVIOUS day's reporting window. After this hour, data belongs to the new day.
# Example with CUTOFF_HOUR_WIB = 9: at 09:01 WIB today, yesterday's data is
# archived and all forms reset for today's new window.
CUTOFF_HOUR_WIB = 9
CUTOFF_MINUTE_WIB = 0
ALLOWED_ROLES = {"admin", "piket", "tim_lid", "tim_kontra", "tim_gal", "tim_medmon", "tim_geoint"}
COG_CHOICES = {"aceh", "jakarta", "indonesia", "papua", "internasional"}

app = FastAPI(title="BAIS Summary Geospasika")
api = APIRouter(prefix="/api")


# ===================== AUTH HELPERS =====================
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def get_jwt_secret() -> str:
    return os.environ["JWT_SECRET"]


def create_access_token(user_id: str, email: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=12),
        "type": "access",
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return {
            "id": str(user["_id"]),
            "email": user["email"],
            "name": user.get("name", ""),
            "role": user["role"],
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_role(*roles):
    async def dep(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in roles and user["role"] != "admin":
            raise HTTPException(status_code=403, detail=f"Forbidden. Required: {roles}")
        return user
    return dep


# ===================== AUTH MODELS =====================
class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: Literal["admin", "piket", "tim_lid", "tim_kontra", "tim_gal", "tim_medmon", "tim_geoint"]


# ===================== AUTH ENDPOINTS =====================
@api.post("/auth/login")
async def login(payload: LoginIn, response: Response):
    email = payload.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email atau password salah")
    token = create_access_token(str(user["_id"]), user["email"], user["role"])
    response.set_cookie(
        key="access_token", value=token, httponly=True, secure=False,
        samesite="lax", max_age=43200, path="/",
    )
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "name": user.get("name", ""),
        "role": user["role"],
        "token": token,
    }


@api.post("/auth/logout")
async def logout(response: Response, _user: dict = Depends(get_current_user)):
    response.delete_cookie("access_token", path="/")
    return {"ok": True}


@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user


@api.post("/auth/register")
async def register(payload: RegisterIn, user: dict = Depends(require_role("admin"))):
    email = payload.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email sudah terdaftar")
    doc = {
        "email": email,
        "password_hash": hash_password(payload.password),
        "name": payload.name,
        "role": payload.role,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    res = await db.users.insert_one(doc)
    return {"id": str(res.inserted_id), "email": email, "name": payload.name, "role": payload.role}


@api.get("/auth/users")
async def list_users(_user: dict = Depends(require_role("admin"))):
    out = []
    async for u in db.users.find({}, {"password_hash": 0}):
        u["id"] = str(u["_id"])
        del u["_id"]
        out.append(u)
    return out


class UserUpdateIn(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[str] = None


@api.patch("/auth/users/{uid}")
async def update_user(uid: str, payload: UserUpdateIn, user: dict = Depends(require_role("admin"))):
    try:
        oid = ObjectId(uid)
    except Exception:
        raise HTTPException(400, "Invalid id")
    target = await db.users.find_one({"_id": oid})
    if not target:
        raise HTTPException(404, "User tidak ditemukan")
    update = {}
    if payload.name is not None:
        update["name"] = payload.name
    if payload.email is not None:
        new_email = payload.email.lower()
        if new_email != target["email"]:
            if await db.users.find_one({"email": new_email}):
                raise HTTPException(400, "Email sudah digunakan")
            update["email"] = new_email
    if payload.role is not None:
        if payload.role not in ALLOWED_ROLES:
            raise HTTPException(400, "Role tidak valid")
        # Prevent demoting the last admin
        if target.get("role") == "admin" and payload.role != "admin":
            n_admin = await db.users.count_documents({"role": "admin"})
            if n_admin <= 1:
                raise HTTPException(400, "Tidak bisa demote admin terakhir")
        update["role"] = payload.role
    if payload.password:
        if len(payload.password) < 6:
            raise HTTPException(400, "Password minimal 6 karakter")
        update["password_hash"] = hash_password(payload.password)
    if not update:
        raise HTTPException(400, "Tidak ada perubahan")
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.users.update_one({"_id": oid}, {"$set": update})
    new_doc = await db.users.find_one({"_id": oid}, {"password_hash": 0})
    new_doc["id"] = str(new_doc["_id"]); del new_doc["_id"]
    return new_doc


@api.delete("/auth/users/{uid}")
async def delete_user(uid: str, user: dict = Depends(require_role("admin"))):
    try:
        oid = ObjectId(uid)
    except Exception:
        raise HTTPException(400, "Invalid id")
    if uid == user["id"]:
        raise HTTPException(400, "Tidak bisa hapus akun sendiri")
    target = await db.users.find_one({"_id": oid})
    if not target:
        raise HTTPException(404, "User tidak ditemukan")
    if target.get("role") == "admin":
        n_admin = await db.users.count_documents({"role": "admin"})
        if n_admin <= 1:
            raise HTTPException(400, "Tidak bisa hapus admin terakhir")
    await db.users.delete_one({"_id": oid})
    return {"ok": True}


# ===================== REPORT MODELS (loose: dict bodies) =====================
# We store: collection per team, each doc has report_date (YYYY-MM-DD), created_by, created_at, payload fields.

def today_wib_date_str() -> str:
    """Effective input date — aligned to CUTOFF_HOUR_WIB cycle.
    Items entered BEFORE the cutoff hour belong to the previous day's reporting window."""
    now = datetime.now(WIB)
    if now.time() < dtime(CUTOFF_HOUR_WIB, CUTOFF_MINUTE_WIB):
        return (now.date() - timedelta(days=1)).isoformat()
    return now.date().isoformat()


def report_date_for_generation() -> str:
    """If before cutoff hour WIB -> yesterday, otherwise -> today."""
    now = datetime.now(WIB)
    if now.time() < dtime(CUTOFF_HOUR_WIB, CUTOFF_MINUTE_WIB):
        return (now.date() - timedelta(days=1)).isoformat()
    return now.date().isoformat()


async def insert_report(collection: str, data: dict, user: dict, report_date: Optional[str] = None) -> dict:
    rd = report_date or today_wib_date_str()
    doc = {
        **data,
        "report_date": rd,
        "created_by": user["id"],
        "created_by_name": user.get("name", ""),
        "created_by_role": user["role"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    res = await db[collection].insert_one(doc)
    doc["id"] = str(res.inserted_id)
    doc.pop("_id", None)
    return doc


def _serialize(doc: dict) -> dict:
    doc["id"] = str(doc["_id"])
    del doc["_id"]
    return doc


async def update_report(collection: str, rid: str, data: dict, user: dict) -> dict:
    """Update an existing report. Preserves report_date/created_by/created_at, refreshes updated_at."""
    update = {
        **data,
        "updated_by": user["id"],
        "updated_by_name": user.get("name", ""),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db[collection].update_one({"_id": ObjectId(rid)}, {"$set": update})
    doc = await db[collection].find_one({"_id": ObjectId(rid)})
    if not doc:
        raise HTTPException(404, "Not found")
    return _serialize(doc)


# ===================== TIM LID =====================
# 4 berita trending: 3 COG + 1 Internasional
# Fields: cog, judul, link, fakta, analisa, tindakan, rekomendasi, sentiment_image (base64)
class LidIn(BaseModel):
    cog: Literal["aceh", "jakarta", "indonesia", "papua", "internasional"]
    judul: str
    link: str
    fakta: str
    analisa: str
    tindakan: str
    rekomendasi: str


@api.post("/lid")
async def create_lid(payload: LidIn, user: dict = Depends(require_role("tim_lid"))):
    return await insert_report("lid_reports", payload.model_dump(), user)


async def list_with_fallback(collection: str, report_date: Optional[str], fallback_previous: bool = False):
    """Return items for the requested report_date. If empty AND fallback_previous=True,
    return items for the most recent earlier date that has data."""
    q = {"report_date": report_date} if report_date else {}
    cur = db[collection].find(q).sort("created_at", -1)
    items = [_serialize(d) async for d in cur]
    if items or not (report_date and fallback_previous):
        return items
    # find most recent earlier date with data
    prev = await db[collection].find_one({"report_date": {"$lt": report_date}}, sort=[("report_date", -1)])
    if not prev:
        return []
    prev_date = prev.get("report_date")
    cur2 = db[collection].find({"report_date": prev_date}).sort("created_at", -1)
    return [_serialize(d) async for d in cur2]


@api.get("/lid")
async def list_lid(report_date: Optional[str] = None, fallback_previous: bool = False,
                   _user: dict = Depends(get_current_user)):
    return await list_with_fallback("lid_reports", report_date, fallback_previous)


@api.put("/lid/{rid}")
async def update_lid(rid: str, payload: LidIn, user: dict = Depends(require_role("tim_lid", "admin"))):
    return await update_report("lid_reports", rid, payload.model_dump(), user)


@api.delete("/lid/{rid}")
async def delete_lid(rid: str, _user: dict = Depends(require_role("tim_lid", "admin"))):
    await db.lid_reports.delete_one({"_id": ObjectId(rid)})
    return {"ok": True}


# ===================== TIM KONTRA =====================
class KontraIn(BaseModel):
    sumber: Literal["to_satgas", "to_internal"]
    tipe: Literal["perorangan", "group"]
    nama_to: str
    data_diri: str
    medsos: List[str] = Field(default_factory=list)  # list of urls
    sna_image: Optional[str] = None
    lainnya_image: Optional[str] = None
    keterangan: str = ""


@api.post("/kontra")
async def create_kontra(payload: KontraIn, user: dict = Depends(require_role("tim_kontra"))):
    return await insert_report("kontra_reports", payload.model_dump(), user)


@api.get("/kontra")
async def list_kontra(report_date: Optional[str] = None, fallback_previous: bool = False,
                     _user: dict = Depends(get_current_user)):
    return await list_with_fallback("kontra_reports", report_date, fallback_previous)


@api.put("/kontra/{rid}")
async def update_kontra(rid: str, payload: KontraIn, user: dict = Depends(require_role("tim_kontra", "admin"))):
    return await update_report("kontra_reports", rid, payload.model_dump(), user)


@api.delete("/kontra/{rid}")
async def delete_kontra(rid: str, _user: dict = Depends(require_role("tim_kontra", "admin"))):
    await db.kontra_reports.delete_one({"_id": ObjectId(rid)})
    return {"ok": True}


# ===================== TIM GAL =====================
class GalIn(BaseModel):
    # Accept legacy "medsos" as alias; will be coerced to "meme" via validator below
    kategori: Literal["narasi", "video", "meme", "medsos"]
    judul: str
    gambar: Optional[str] = None  # base64
    links: List[str] = Field(default_factory=list)
    keterangan: str = ""

    @field_validator("kategori", mode="before")
    @classmethod
    def _coerce_medsos_to_meme(cls, v):
        if isinstance(v, str) and v.strip().lower() == "medsos":
            return "meme"
        return v


@api.post("/gal")
async def create_gal(payload: GalIn, user: dict = Depends(require_role("tim_gal"))):
    return await insert_report("gal_reports", payload.model_dump(), user)


@api.get("/gal")
async def list_gal(report_date: Optional[str] = None, fallback_previous: bool = False,
                   _user: dict = Depends(get_current_user)):
    return await list_with_fallback("gal_reports", report_date, fallback_previous)


@api.put("/gal/{rid}")
async def update_gal(rid: str, payload: GalIn, user: dict = Depends(require_role("tim_gal", "admin"))):
    return await update_report("gal_reports", rid, payload.model_dump(), user)


@api.delete("/gal/{rid}")
async def delete_gal(rid: str, _user: dict = Depends(require_role("tim_gal", "admin"))):
    await db.gal_reports.delete_one({"_id": ObjectId(rid)})
    return {"ok": True}


# ----- TIM GAL: Statistik Penggalangan per Platform -----
# One document per report_date — upserted by tim_gal.
# Structure: counts[kategori][platform] = int
GAL_PLATFORMS = ["instagram", "facebook", "twitter", "tiktok", "youtube", "threads", "media_online"]
GAL_CATEGORIES = ["narasi", "video", "meme"]


class GalStatsPayload(BaseModel):
    counts: dict[str, dict[str, int]] = Field(default_factory=dict)
    report_date: Optional[str] = None

    @field_validator("counts", mode="before")
    @classmethod
    def _normalize_counts(cls, v):
        if not isinstance(v, dict):
            return {}
        out = {}
        for cat in GAL_CATEGORIES:
            row = v.get(cat) or {}
            out[cat] = {p: int(max(0, row.get(p) or 0)) for p in GAL_PLATFORMS}
        return out


@api.post("/gal/stats")
async def upsert_gal_stats(
    payload: GalStatsPayload,
    user: dict = Depends(require_role("tim_gal", "admin")),
):
    rd = payload.report_date or today_wib_date_str()
    now_iso = datetime.now(timezone.utc).isoformat()
    doc = {
        "report_date": rd,
        "counts": payload.counts,
        "updated_at": now_iso,
        "updated_by": user["id"],
        "updated_by_name": user.get("name", ""),
    }
    await db.gal_stats_reports.update_one(
        {"report_date": rd},
        {"$set": doc, "$setOnInsert": {"created_at": now_iso}},
        upsert=True,
    )
    return {"ok": True, **doc}


@api.get("/gal/stats")
async def get_gal_stats(
    report_date: Optional[str] = None,
    fallback_previous: bool = False,
    _user: dict = Depends(get_current_user),
):
    rd = report_date or today_wib_date_str()
    doc = await db.gal_stats_reports.find_one({"report_date": rd})
    if not doc and fallback_previous:
        from datetime import date as _d, timedelta as _td
        try:
            prev = (_d.fromisoformat(rd) - _td(days=1)).isoformat()
            doc = await db.gal_stats_reports.find_one({"report_date": prev})
        except Exception:
            pass
    if not doc:
        # Empty zeros
        return {
            "report_date": rd,
            "counts": {c: {p: 0 for p in GAL_PLATFORMS} for c in GAL_CATEGORIES},
            "updated_at": None,
        }
    doc.pop("_id", None)
    # Backfill missing categories/platforms
    counts = doc.get("counts") or {}
    for c in GAL_CATEGORIES:
        counts.setdefault(c, {})
        for p in GAL_PLATFORMS:
            counts[c].setdefault(p, 0)
    doc["counts"] = counts
    return doc


# ===================== TIM MEDMON =====================
class MedmonItem(BaseModel):
    judul: str
    link: str
    sentiment: Literal["positif", "negatif"]


class MedmonIn(BaseModel):
    subjek: str  # "Presiden", "Panglima TNI", "MBG", or custom
    berita: List[MedmonItem] = Field(default_factory=list)
    chart_sumber_image: Optional[str] = None
    sentiment_positif: float = 0
    sentiment_negatif: float = 0
    sentiment_netral: float = 0
    analisa: str = ""
    rekomendasi: str = ""


@api.post("/medmon")
async def create_medmon(payload: MedmonIn, user: dict = Depends(require_role("tim_medmon"))):
    data = payload.model_dump()
    return await insert_report("medmon_reports", data, user)


@api.get("/medmon")
async def list_medmon(report_date: Optional[str] = None, fallback_previous: bool = False,
                     _user: dict = Depends(get_current_user)):
    return await list_with_fallback("medmon_reports", report_date, fallback_previous)


@api.put("/medmon/{rid}")
async def update_medmon(rid: str, payload: MedmonIn, user: dict = Depends(require_role("tim_medmon", "admin"))):
    return await update_report("medmon_reports", rid, payload.model_dump(), user)


@api.delete("/medmon/{rid}")
async def delete_medmon(rid: str, _user: dict = Depends(require_role("tim_medmon", "admin"))):
    await db.medmon_reports.delete_one({"_id": ObjectId(rid)})
    return {"ok": True}


# ===================== TIM GEOINT =====================
class GeointIn(BaseModel):
    wilayah: str
    nama_orang: str
    no_hp: str = ""
    lat: float
    lon: float
    peta_image: Optional[str] = None
    status: Literal["aktif", "tidak_aktif"]
    keterangan: str = ""


@api.post("/geoint")
async def create_geoint(payload: GeointIn, user: dict = Depends(require_role("tim_geoint"))):
    return await insert_report("geoint_reports", payload.model_dump(), user)


@api.get("/geoint")
async def list_geoint(report_date: Optional[str] = None, fallback_previous: bool = False,
                     _user: dict = Depends(get_current_user)):
    return await list_with_fallback("geoint_reports", report_date, fallback_previous)


@api.put("/geoint/{rid}")
async def update_geoint(rid: str, payload: GeointIn, user: dict = Depends(require_role("tim_geoint", "admin"))):
    return await update_report("geoint_reports", rid, payload.model_dump(), user)


@api.delete("/geoint/{rid}")
async def delete_geoint(rid: str, _user: dict = Depends(require_role("tim_geoint", "admin"))):
    await db.geoint_reports.delete_one({"_id": ObjectId(rid)})
    return {"ok": True}


# ===================== PIKET (TEK / SANDI / MEDIS) =====================
class PiketIn(BaseModel):
    satgas: Literal["tek", "sandi", "medis"]
    judul: str
    isi: str
    gambar: Optional[str] = None


@api.post("/piket")
async def create_piket(payload: PiketIn, user: dict = Depends(require_role("piket"))):
    return await insert_report("piket_reports", payload.model_dump(), user)


@api.get("/piket")
async def list_piket(report_date: Optional[str] = None, fallback_previous: bool = False,
                    _user: dict = Depends(get_current_user)):
    return await list_with_fallback("piket_reports", report_date, fallback_previous)


@api.put("/piket/{rid}")
async def update_piket(rid: str, payload: PiketIn, user: dict = Depends(require_role("piket", "admin"))):
    return await update_report("piket_reports", rid, payload.model_dump(), user)


@api.delete("/piket/{rid}")
async def delete_piket(rid: str, _user: dict = Depends(require_role("piket", "admin"))):
    await db.piket_reports.delete_one({"_id": ObjectId(rid)})
    return {"ok": True}


# ===================== SEARCH ACROSS ALL REPORTS =====================
import re as _re_search


def _strip_html_lite(s: str) -> str:
    """Strip basic HTML tags so search text matches plainly."""
    if not s:
        return ""
    return _re_search.sub(r"<[^>]+>", " ", str(s))


def _make_snippets(text: str, query: str, max_snips: int = 3,
                   context_chars: int = 90) -> List[Dict[str, Any]]:
    """Find query occurrences and return up to max_snips of {snippet, start} dicts.
    `start` is the offset in the FULL text where the match begins (so frontend
    can scroll to it). `snippet` is a short context around the match."""
    if not text or not query:
        return []
    out = []
    plain = text
    qlow = query.lower()
    plow = plain.lower()
    pos = 0
    while pos < len(plow) and len(out) < max_snips:
        idx = plow.find(qlow, pos)
        if idx < 0:
            break
        s = max(0, idx - context_chars)
        e = min(len(plain), idx + len(query) + context_chars)
        prefix = "..." if s > 0 else ""
        suffix = "..." if e < len(plain) else ""
        out.append({
            "snippet": prefix + plain[s:e] + suffix,
            "match_at": idx,
            "match_len": len(query),
        })
        pos = idx + len(query)
    return out


SEARCHABLE_COLLECTIONS = [
    # (collection_name, type_key, title_field, searchable_fields, badge)
    ("lid_reports", "lid", "judul",
     ["judul", "fakta", "analisa", "tindakan", "rekomendasi", "link", "cog"], "TIM LID"),
    ("kontra_reports", "kontra", "nama_to",
     ["nama_to", "data_diri", "keterangan", "sumber", "tipe"], "TIM KONTRA"),
    ("gal_reports", "gal", "judul",
     ["judul", "keterangan", "kategori"], "TIM GAL"),
    ("medmon_reports", "medmon", "subjek",
     ["subjek", "ringkasan", "analisa", "rekomendasi"], "TIM MEDMON"),
    ("piket_reports", "piket", "judul",
     ["judul", "isi", "satgas"], "PIKET"),
    ("geoint_reports", "geoint", "nama_orang",
     ["nama_orang", "wilayah", "status"], "TIM GEOINT"),
]


@api.get("/search")
async def search_reports(
    q: str = "",
    limit: int = 50,
    _user: dict = Depends(get_current_user),
):
    """Full-text search across all team reports. Returns matching items with
    snippets so the UI can preview & highlight. Case-insensitive."""
    q = (q or "").strip()
    if len(q) < 2:
        return {"query": q, "total": 0, "results": []}

    safe_q = _re_search.escape(q)
    rx = {"$regex": safe_q, "$options": "i"}

    results: List[Dict[str, Any]] = []
    for coll_name, type_key, title_field, fields, badge in SEARCHABLE_COLLECTIONS:
        # Build OR filter — also search special list field for GAL (links)
        or_clauses = [{f: rx} for f in fields]
        if type_key == "gal":
            or_clauses.append({"links": rx})
        if type_key == "kontra":
            or_clauses.append({"medsos": rx})
        try:
            cursor = db[coll_name].find({"$or": or_clauses}).limit(int(limit))
            async for doc in cursor:
                # Build a flat text representation for snippet extraction
                pieces = []
                doc_view: Dict[str, Any] = {}
                for f in fields + (["links"] if type_key == "gal" else []) + (["medsos"] if type_key == "kontra" else []):
                    v = doc.get(f)
                    if v is None:
                        continue
                    if isinstance(v, list):
                        for item in v:
                            if isinstance(item, str):
                                pieces.append((f, item))
                                doc_view[f] = doc_view.get(f, []) + [item] if isinstance(doc_view.get(f), list) else [item]
                    else:
                        s = _strip_html_lite(str(v))
                        if s:
                            pieces.append((f, s))
                            doc_view[f] = s
                # Find snippets per field
                field_snippets: List[Dict[str, Any]] = []
                for f, txt in pieces:
                    sn = _make_snippets(txt, q, max_snips=2, context_chars=70)
                    for s in sn:
                        s["field"] = f
                        field_snippets.append(s)
                    if len(field_snippets) >= 5:
                        break
                if not field_snippets:
                    # fallback: include first 120 chars of any populated field
                    for f, txt in pieces[:1]:
                        field_snippets.append({
                            "field": f, "snippet": txt[:160],
                            "match_at": -1, "match_len": 0,
                        })
                results.append({
                    "id": str(doc.get("_id")),
                    "type": type_key,
                    "badge": badge,
                    "report_date": doc.get("report_date") or "",
                    "title": str(doc.get(title_field, "") or "Tanpa Judul"),
                    "snippets": field_snippets[:5],
                    "full_doc": _serialize_doc_for_search(doc, type_key),
                })
                if len(results) >= int(limit):
                    break
        except Exception as e:
            log.warning(f"search error in {coll_name}: {e}")
        if len(results) >= int(limit):
            break

    # Sort: most recent first
    results.sort(key=lambda r: (r.get("report_date") or "", r.get("title", "")), reverse=True)
    return {"query": q, "total": len(results), "results": results[: int(limit)]}


def _serialize_doc_for_search(doc: dict, type_key: str) -> dict:
    """Return a plain JSON-safe dict for the document with HTML stripped where
    relevant, ready for the frontend preview."""
    out = {}
    for k, v in doc.items():
        if k == "_id":
            continue
        if isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
        elif isinstance(v, list):
            out[k] = [
                _strip_html_lite(i) if isinstance(i, str) else i for i in v
            ]
        elif isinstance(v, str):
            out[k] = _strip_html_lite(v)
        else:
            out[k] = v
    out["_type"] = type_key
    return out


# ===================== AGGREGATION / DAILY DATA =====================
async def collect_daily_data(report_date: str) -> dict:
    q = {"report_date": report_date}
    lid = [_serialize(d) async for d in db.lid_reports.find(q)]
    kontra = [_serialize(d) async for d in db.kontra_reports.find(q)]
    gal = [_serialize(d) async for d in db.gal_reports.find(q)]
    medmon = [_serialize(d) async for d in db.medmon_reports.find(q)]
    geoint = [_serialize(d) async for d in db.geoint_reports.find(q)]
    piket = [_serialize(d) async for d in db.piket_reports.find(q)]
    # Tim GAL platform statistics (one doc per report_date)
    gal_stats_doc = await db.gal_stats_reports.find_one(q)
    gal_stats = (gal_stats_doc or {}).get("counts") or {}
    return {
        "report_date": report_date,
        "lid": lid,
        "kontra": kontra,
        "gal": gal,
        "gal_stats": gal_stats,
        "medmon": medmon,
        "geoint": geoint,
        "piket": piket,
    }


async def collect_medmon_7day_trend(report_date: str) -> dict:
    """Return last-7-days sentiment trend per MEDMON subject ending at report_date (inclusive).
    Shape: {"dates": ["YYYY-MM-DD", ...x7], "subjects": {"Presiden": [{date, pos, neg, net}, ...x7], ...}}
    Missing days are filled with zeros (gap in chart line).
    """
    from datetime import date as _date, timedelta as _td
    try:
        end = _date.fromisoformat(report_date)
    except Exception:
        end = datetime.now(WIB).date()
    dates = [(end - _td(days=6 - i)).isoformat() for i in range(7)]
    cursor = db.medmon_reports.find({"report_date": {"$in": dates}})
    by_date: dict = {}
    async for doc in cursor:
        rd = doc.get("report_date")
        subj = (doc.get("subjek") or "-").strip()
        by_date.setdefault(rd, {})[subj] = {
            "pos": float(doc.get("sentiment_positif") or 0),
            "neg": float(doc.get("sentiment_negatif") or 0),
            "net": float(doc.get("sentiment_netral") or 0),
        }
    # Union of all subjects appearing in any of the 7 days
    all_subjects: list = []
    for rd in dates:
        for s in (by_date.get(rd) or {}).keys():
            if s not in all_subjects:
                all_subjects.append(s)
    subjects: dict = {}
    for s in all_subjects:
        series = []
        for rd in dates:
            v = (by_date.get(rd) or {}).get(s)
            series.append({"date": rd, "pos": v["pos"] if v else 0, "neg": v["neg"] if v else 0, "net": v["net"] if v else 0, "present": v is not None})
        subjects[s] = series
    return {"dates": dates, "subjects": subjects}


@api.get("/daily")
async def daily(report_date: Optional[str] = None, _user: dict = Depends(get_current_user)):
    rd = report_date or report_date_for_generation()
    data = await collect_daily_data(rd)
    return data


@api.get("/daily/info")
async def daily_info(_user: dict = Depends(get_current_user)):
    """Returns the effective report date (yesterday if before cutoff WIB, else today) and now WIB."""
    now = datetime.now(WIB)
    cutoff = dtime(CUTOFF_HOUR_WIB, CUTOFF_MINUTE_WIB)
    return {
        "now_wib": now.isoformat(),
        "report_date": report_date_for_generation(),
        "input_date": today_wib_date_str(),
        "before_cutoff": now.time() < cutoff,
        "before_noon": now.time() < cutoff,  # legacy alias for older clients
        "cutoff_hour": CUTOFF_HOUR_WIB,
        "cutoff_minute": CUTOFF_MINUTE_WIB,
    }


# ===================== AI SUMMARY =====================
@api.post("/summary/ai")
async def ai_summary(
    report_date: Optional[str] = Body(None, embed=True),
    user: dict = Depends(require_role("admin", "piket")),
):
    rd = report_date or report_date_for_generation()
    data = await collect_daily_data(rd)
    text = await generate_ai_summary(data)
    if text.startswith("[AI SUMMARY ERROR]") or text.startswith("[AI SUMMARY UNAVAILABLE]"):
        raise HTTPException(status_code=502, detail=text)
    # markdown -> html for editor consumption
    from md_to_html import md_to_html
    html = md_to_html(text)
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.ai_summaries.update_one(
        {"report_date": rd},
        {"$set": {
            "text": text,
            "html": html,
            "generated_at": now_iso,
            "edited_at": None,
            "generated_by": user["id"],
        }},
        upsert=True,
    )
    return {"report_date": rd, "summary": text, "html": html}


@api.patch("/summary/ai")
async def ai_summary_edit(
    report_date: str = Body(..., embed=True),
    html: str = Body(..., embed=True),
    user: dict = Depends(require_role("admin", "piket")),
):
    res = await db.ai_summaries.update_one(
        {"report_date": report_date},
        {"$set": {
            "html": html,
            "edited_at": datetime.now(timezone.utc).isoformat(),
            "edited_by": user["id"],
        }},
        upsert=True,
    )
    return {"ok": True, "modified": res.modified_count}


@api.get("/summary/ai")
async def get_ai_summary(report_date: Optional[str] = None, _user: dict = Depends(get_current_user)):
    rd = report_date or report_date_for_generation()
    doc = await db.ai_summaries.find_one({"report_date": rd})
    if not doc:
        return {"report_date": rd, "summary": None, "html": None}
    return {
        "report_date": rd,
        "summary": doc.get("text"),
        "html": doc.get("html"),
        "generated_at": doc.get("generated_at"),
        "edited_at": doc.get("edited_at"),
    }


# ===================== PDF GENERATION =====================
@api.get("/pdf")
async def generate_pdf(report_date: Optional[str] = None, user: dict = Depends(require_role("admin", "piket"))):
    # Determine date with the cutoff hour WIB rule
    today = datetime.now(WIB).date().isoformat()
    rd = report_date or report_date_for_generation()
    if rd == today and datetime.now(WIB).time() < dtime(CUTOFF_HOUR_WIB, CUTOFF_MINUTE_WIB):
        raise HTTPException(
            status_code=400,
            detail=f"Laporan tanggal hari ini hanya bisa di-generate setelah pukul {CUTOFF_HOUR_WIB:02d}:{CUTOFF_MINUTE_WIB:02d} WIB.",
        )
    data = await collect_daily_data(rd)
    # 7-day MEDMON sentiment trend for the trend chart on page 1
    data["medmon_trend"] = await collect_medmon_7day_trend(rd)
    # Get cached AI summary if any — prefer edited HTML over raw text
    ai_doc = await db.ai_summaries.find_one({"report_date": rd})
    ai_text = ai_doc.get("text") if ai_doc else None
    ai_html = ai_doc.get("html") if ai_doc else None
    # Run heavy sync PDF generation (incl. OSM tile fetch, PIL drawing) in a
    # threadpool so it doesn't block the asyncio event loop. This is what lets
    # ~20 concurrent users hit the system without one PDF stalling all others.
    pdf_bytes = await run_in_threadpool(build_summary_pdf, data, ai_text, ai_html=ai_html)
    filename = f"BAIS_Summary_{rd}.pdf"

    # Persist to history (generated_reports) — keep only the LATEST per report_date
    import base64 as _b64
    counts = {k: len(data.get(k, [])) for k in ["lid", "kontra", "gal", "medmon", "geoint", "piket"]}
    # Single atomic upsert (replaces previous delete_many+insert_one race)
    await db.generated_reports.replace_one(
        {"report_date": rd},
        {
            "report_date": rd,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generated_by": user["id"],
            "generated_by_name": user.get("name", ""),
            "filename": filename,
            "size_bytes": len(pdf_bytes),
            "pdf_base64": _b64.b64encode(pdf_bytes).decode("ascii"),
            "counts": counts,
            "has_ai_summary": bool(ai_text),
        },
        upsert=True,
    )

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _safe_objid(rid: str) -> ObjectId:
    try:
        return ObjectId(rid)
    except Exception:
        raise HTTPException(status_code=404, detail="ID tidak valid")


# ===================== REPORT HISTORY =====================
@api.get("/reports/history")
async def reports_history(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    _user: dict = Depends(require_role("admin", "piket")),
):
    q = {}
    if start_date or end_date:
        q["report_date"] = {}
        if start_date:
            q["report_date"]["$gte"] = start_date
        if end_date:
            q["report_date"]["$lte"] = end_date
    cur = db.generated_reports.find(q, {"pdf_base64": 0}).sort("generated_at", -1).limit(min(limit, 500))
    out = []
    async for d in cur:
        d["id"] = str(d["_id"])
        del d["_id"]
        # Compute team attendance for this report_date
        rd = d.get("report_date")
        attendance = {}
        team_cols = {
            "lid": "lid_reports", "kontra": "kontra_reports", "gal": "gal_reports",
            "medmon": "medmon_reports", "geoint": "geoint_reports", "piket": "piket_reports",
        }
        for key, col in team_cols.items():
            n = await db[col].count_documents({"report_date": rd}) if rd else 0
            attendance[key] = n
        d["attendance"] = attendance
        out.append(d)
    return out


@api.get("/reports/{rid}/download")
async def reports_download(rid: str, _user: dict = Depends(require_role("admin", "piket"))):
    import base64 as _b64
    doc = await db.generated_reports.find_one({"_id": _safe_objid(rid)})
    if not doc:
        raise HTTPException(status_code=404, detail="Laporan tidak ditemukan")
    pdf_bytes = _b64.b64decode(doc["pdf_base64"])
    filename = doc.get("filename") or f"BAIS_Summary_{doc.get('report_date','')}.pdf"
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@api.delete("/reports/{rid}")
async def reports_delete(rid: str, _user: dict = Depends(require_role("admin"))):
    res = await db.generated_reports.delete_one({"_id": _safe_objid(rid)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Laporan tidak ditemukan")
    return {"ok": True}


# ===================== STARTUP / SEEDING =====================
@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.lid_reports.create_index([("report_date", -1)])
    await db.kontra_reports.create_index([("report_date", -1)])
    await db.gal_reports.create_index([("report_date", -1)])
    await db.medmon_reports.create_index([("report_date", -1)])
    await db.geoint_reports.create_index([("report_date", -1)])
    await db.piket_reports.create_index([("report_date", -1)])
    await db.ai_summaries.create_index("report_date", unique=True)
    await db.generated_reports.create_index([("report_date", -1)])
    await db.generated_reports.create_index([("generated_at", -1)])

    # Seed admin and test users
    seed_users = [
        ("admin@bais.tni.mil.id", "Bais2026!", "Admin BAIS", "admin"),
        ("piket@bais.tni.mil.id", "Piket2026!", "Piket Operasi", "piket"),
        ("lid@bais.tni.mil.id", "Lid2026!", "Tim LID", "tim_lid"),
        ("kontra@bais.tni.mil.id", "Kontra2026!", "Tim Kontra", "tim_kontra"),
        ("gal@bais.tni.mil.id", "Gal2026!", "Tim Galang", "tim_gal"),
        ("medmon@bais.tni.mil.id", "Medmon2026!", "Tim Medmon", "tim_medmon"),
        ("geoint@bais.tni.mil.id", "Geoint2026!", "Tim Geoint", "tim_geoint"),
    ]
    for email, pwd, name, role in seed_users:
        # Atomic upsert (race-safe for multi-worker startup)
        await db.users.update_one(
            {"email": email},
            {
                "$setOnInsert": {
                    "email": email,
                    "password_hash": hash_password(pwd),
                    "name": name,
                    "role": role,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            },
            upsert=True,
        )
        # Re-sync password if changed via env
        existing = await db.users.find_one({"email": email})
        if existing and not verify_password(pwd, existing["password_hash"]):
            await db.users.update_one(
                {"_id": existing["_id"]},
                {"$set": {"password_hash": hash_password(pwd)}},
            )
    logger.info("Startup complete. Users seeded.")

    # Migration: legacy "medsos" → "meme" in gal_reports
    try:
        res = await db.gal_reports.update_many(
            {"kategori": "medsos"}, {"$set": {"kategori": "meme"}}
        )
        if res.modified_count:
            logger.info(f"Migrated {res.modified_count} gal_reports kategori 'medsos' → 'meme'")
    except Exception as e:
        logger.warning(f"GAL kategori migration skipped: {e}")

    # Indexes for high-concurrency read paths (20+ simultaneous users)
    try:
        for coll in [
            "lid_reports", "kontra_reports", "gal_reports",
            "medmon_reports", "geoint_reports", "piket_reports",
        ]:
            await db[coll].create_index("report_date")
            await db[coll].create_index([("report_date", 1), ("updated_at", -1)])
        await db.generated_reports.create_index("report_date", unique=True)
        await db.ai_summaries.create_index("report_date", unique=True)
        await db.gal_stats_reports.create_index("report_date", unique=True)
        await db.users.create_index("email", unique=True)
        logger.info("Indexes ensured for high-concurrency reads.")
    except Exception as e:
        logger.warning(f"Index creation skipped: {e}")


@app.on_event("shutdown")
async def shutdown():
    client.close()


# ===================== APP =====================
app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@api.get("/")
async def root():
    return {"app": "BAIS Summary Geospasika", "status": "ok"}
