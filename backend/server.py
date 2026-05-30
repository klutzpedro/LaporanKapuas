"""BAIS Summary Geospasika - FastAPI backend (single-file)."""
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import logging
import secrets
from datetime import datetime, timezone, timedelta, time as dtime, date as ddate
from typing import Optional, List, Literal

import bcrypt
import jwt
from bson import ObjectId
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, Body
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
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
ALLOWED_ROLES = {"admin", "piket", "tim_lid", "tim_kontra", "tim_gal", "tim_medmon", "tim_geoint"}
COG_CHOICES = {"aceh", "jakarta", "papua", "internasional"}

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


# ===================== REPORT MODELS (loose: dict bodies) =====================
# We store: collection per team, each doc has report_date (YYYY-MM-DD), created_by, created_at, payload fields.

def today_wib_date_str() -> str:
    """Effective input date — aligned to 12:00 WIB cycle.
    Items entered BEFORE 12:00 WIB belong to the previous day's reporting window."""
    now = datetime.now(WIB)
    if now.time() < dtime(12, 0):
        return (now.date() - timedelta(days=1)).isoformat()
    return now.date().isoformat()


def report_date_for_generation() -> str:
    """If before 12:00 WIB -> yesterday, otherwise -> today."""
    now = datetime.now(WIB)
    if now.time() < dtime(12, 0):
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
    cog: Literal["aceh", "jakarta", "papua", "internasional"]
    judul: str
    link: str
    fakta: str
    analisa: str
    tindakan: str
    rekomendasi: str
    sentiment_positif: int = 0
    sentiment_negatif: int = 0
    sentiment_netral: int = 0


@api.post("/lid")
async def create_lid(payload: LidIn, user: dict = Depends(require_role("tim_lid"))):
    return await insert_report("lid_reports", payload.model_dump(), user)


@api.get("/lid")
async def list_lid(report_date: Optional[str] = None, _user: dict = Depends(get_current_user)):
    q = {"report_date": report_date} if report_date else {}
    cur = db.lid_reports.find(q).sort("created_at", -1)
    return [_serialize(d) async for d in cur]


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
async def list_kontra(report_date: Optional[str] = None, _user: dict = Depends(get_current_user)):
    q = {"report_date": report_date} if report_date else {}
    cur = db.kontra_reports.find(q).sort("created_at", -1)
    return [_serialize(d) async for d in cur]


@api.put("/kontra/{rid}")
async def update_kontra(rid: str, payload: KontraIn, user: dict = Depends(require_role("tim_kontra", "admin"))):
    return await update_report("kontra_reports", rid, payload.model_dump(), user)


@api.delete("/kontra/{rid}")
async def delete_kontra(rid: str, _user: dict = Depends(require_role("tim_kontra", "admin"))):
    await db.kontra_reports.delete_one({"_id": ObjectId(rid)})
    return {"ok": True}


# ===================== TIM GAL =====================
class GalIn(BaseModel):
    kategori: Literal["narasi", "video", "medsos"]
    judul: str
    gambar: Optional[str] = None  # base64
    links: List[str] = Field(default_factory=list)
    keterangan: str = ""


@api.post("/gal")
async def create_gal(payload: GalIn, user: dict = Depends(require_role("tim_gal"))):
    return await insert_report("gal_reports", payload.model_dump(), user)


@api.get("/gal")
async def list_gal(report_date: Optional[str] = None, _user: dict = Depends(get_current_user)):
    q = {"report_date": report_date} if report_date else {}
    cur = db.gal_reports.find(q).sort("created_at", -1)
    return [_serialize(d) async for d in cur]


@api.put("/gal/{rid}")
async def update_gal(rid: str, payload: GalIn, user: dict = Depends(require_role("tim_gal", "admin"))):
    return await update_report("gal_reports", rid, payload.model_dump(), user)


@api.delete("/gal/{rid}")
async def delete_gal(rid: str, _user: dict = Depends(require_role("tim_gal", "admin"))):
    await db.gal_reports.delete_one({"_id": ObjectId(rid)})
    return {"ok": True}


# ===================== TIM MEDMON =====================
class MedmonItem(BaseModel):
    judul: str
    link: str
    sentiment: Literal["positif", "negatif"]


class MedmonIn(BaseModel):
    subjek: str  # "Presiden", "Panglima TNI", "MBG", or custom
    berita: List[MedmonItem] = Field(default_factory=list)
    pie_sentiment_image: Optional[str] = None
    chart_sumber_image: Optional[str] = None
    analisa: str = ""
    rekomendasi: str = ""


@api.post("/medmon")
async def create_medmon(payload: MedmonIn, user: dict = Depends(require_role("tim_medmon"))):
    data = payload.model_dump()
    return await insert_report("medmon_reports", data, user)


@api.get("/medmon")
async def list_medmon(report_date: Optional[str] = None, _user: dict = Depends(get_current_user)):
    q = {"report_date": report_date} if report_date else {}
    cur = db.medmon_reports.find(q).sort("created_at", -1)
    return [_serialize(d) async for d in cur]


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
    sentiment_positif: int = 0
    sentiment_negatif: int = 0
    sentiment_netral: int = 0


@api.post("/geoint")
async def create_geoint(payload: GeointIn, user: dict = Depends(require_role("tim_geoint"))):
    return await insert_report("geoint_reports", payload.model_dump(), user)


@api.get("/geoint")
async def list_geoint(report_date: Optional[str] = None, _user: dict = Depends(get_current_user)):
    q = {"report_date": report_date} if report_date else {}
    cur = db.geoint_reports.find(q).sort("created_at", -1)
    return [_serialize(d) async for d in cur]


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
async def list_piket(report_date: Optional[str] = None, _user: dict = Depends(get_current_user)):
    q = {"report_date": report_date} if report_date else {}
    cur = db.piket_reports.find(q).sort("created_at", -1)
    return [_serialize(d) async for d in cur]


@api.put("/piket/{rid}")
async def update_piket(rid: str, payload: PiketIn, user: dict = Depends(require_role("piket", "admin"))):
    return await update_report("piket_reports", rid, payload.model_dump(), user)


@api.delete("/piket/{rid}")
async def delete_piket(rid: str, _user: dict = Depends(require_role("piket", "admin"))):
    await db.piket_reports.delete_one({"_id": ObjectId(rid)})
    return {"ok": True}


# ===================== AGGREGATION / DAILY DATA =====================
async def collect_daily_data(report_date: str) -> dict:
    q = {"report_date": report_date}
    lid = [_serialize(d) async for d in db.lid_reports.find(q)]
    kontra = [_serialize(d) async for d in db.kontra_reports.find(q)]
    gal = [_serialize(d) async for d in db.gal_reports.find(q)]
    medmon = [_serialize(d) async for d in db.medmon_reports.find(q)]
    geoint = [_serialize(d) async for d in db.geoint_reports.find(q)]
    piket = [_serialize(d) async for d in db.piket_reports.find(q)]
    return {
        "report_date": report_date,
        "lid": lid,
        "kontra": kontra,
        "gal": gal,
        "medmon": medmon,
        "geoint": geoint,
        "piket": piket,
    }


@api.get("/daily")
async def daily(report_date: Optional[str] = None, _user: dict = Depends(get_current_user)):
    rd = report_date or report_date_for_generation()
    data = await collect_daily_data(rd)
    return data


@api.get("/daily/info")
async def daily_info(_user: dict = Depends(get_current_user)):
    """Returns the effective report date (yesterday if before 12 WIB, else today) and now WIB."""
    now = datetime.now(WIB)
    return {
        "now_wib": now.isoformat(),
        "report_date": report_date_for_generation(),
        "input_date": today_wib_date_str(),
        "before_noon": now.time() < dtime(12, 0),
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
    # Determine date with the 12 WIB rule
    today = datetime.now(WIB).date().isoformat()
    rd = report_date or report_date_for_generation()
    if rd == today and datetime.now(WIB).time() < dtime(12, 0):
        raise HTTPException(status_code=400,
                            detail="Laporan tanggal hari ini hanya bisa di-generate setelah pukul 12:00 WIB.")
    data = await collect_daily_data(rd)
    # Get cached AI summary if any — prefer edited HTML over raw text
    ai_doc = await db.ai_summaries.find_one({"report_date": rd})
    ai_text = ai_doc.get("text") if ai_doc else None
    ai_html = ai_doc.get("html") if ai_doc else None
    pdf_bytes = build_summary_pdf(data, ai_text, ai_html=ai_html)
    filename = f"BAIS_Summary_{rd}.pdf"

    # Persist to history (generated_reports)
    import base64 as _b64
    counts = {k: len(data.get(k, [])) for k in ["lid", "kontra", "gal", "medmon", "geoint", "piket"]}
    await db.generated_reports.insert_one({
        "report_date": rd,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": user["id"],
        "generated_by_name": user.get("name", ""),
        "filename": filename,
        "size_bytes": len(pdf_bytes),
        "pdf_base64": _b64.b64encode(pdf_bytes).decode("ascii"),
        "counts": counts,
        "has_ai_summary": bool(ai_text),
    })

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
        existing = await db.users.find_one({"email": email})
        if not existing:
            await db.users.insert_one({
                "email": email,
                "password_hash": hash_password(pwd),
                "name": name,
                "role": role,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        else:
            # keep password in sync with env-provided values
            if not verify_password(pwd, existing["password_hash"]):
                await db.users.update_one(
                    {"_id": existing["_id"]},
                    {"$set": {"password_hash": hash_password(pwd)}},
                )
    logger.info("Startup complete. Users seeded.")


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
