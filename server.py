from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import logging
import uuid
import bcrypt
import jwt
import hashlib
import asyncio
import json as _json
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Literal
from pathlib import Path as _Path

from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr
from cryptography.fernet import Fernet, InvalidToken
import resend

# ---- Mongo ----
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

# ---- App ----
app = FastAPI(title="Sentinel - AI Video Surveillance")
api = APIRouter(prefix="/api")

JWT_ALGO = "HS256"

# ---- Encrypted recording storage ----
RECORDINGS_DIR = _Path(os.environ.get("RECORDINGS_DIR", "/app/backend/storage/recordings"))
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

_ENC_KEY = os.environ.get("RECORDING_ENCRYPTION_KEY")
if not _ENC_KEY:
    raise RuntimeError("RECORDING_ENCRYPTION_KEY missing from environment")
_FERNET = Fernet(_ENC_KEY.encode())

# ---- Email alert configuration ----
SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}
ALERT_MIN_RANK = SEVERITY_RANK.get(
    os.environ.get("ALERT_MIN_SEVERITY", "medium").lower(), 2
)
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "").strip()
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev").strip()
ALERT_RECIPIENT_EMAIL = os.environ.get("ALERT_RECIPIENT_EMAIL", "").strip()
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

SEVERITY_COLOR = {
    "low": "#34d399",
    "medium": "#fbbf24",
    "high": "#fb923c",
    "critical": "#f43f5e",
}


def _build_alert_html(inc: dict) -> str:
    sev = inc.get("severity", "medium")
    color = SEVERITY_COLOR.get(sev, "#fbbf24")
    confidence_pct = f"{round(float(inc.get('confidence', 0)) * 100)}%"
    return f"""<!doctype html>
<html><body style="margin:0;background:#0d1117;font-family:Arial,Helvetica,sans-serif;color:#f0f6fc;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#0d1117;padding:24px 0;">
  <tr><td align="center">
    <table role="presentation" width="560" cellpadding="0" cellspacing="0" style="background:#11151c;border:1px solid #1f2730;border-radius:4px;overflow:hidden;">
      <tr><td style="padding:18px 24px;border-bottom:1px solid #1f2730;">
        <div style="font-size:11px;letter-spacing:0.2em;text-transform:uppercase;color:#8b949e;font-family:'Courier New',monospace;">// SENTINEL · ALERT</div>
        <div style="margin-top:6px;font-size:20px;font-weight:900;color:#f0f6fc;">Anomaly detected</div>
      </td></tr>
      <tr><td style="padding:24px;">
        <span style="display:inline-block;padding:6px 12px;border:1px solid {color}66;background:{color}1f;color:{color};border-radius:2px;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;font-family:'Courier New',monospace;font-weight:700;">{sev}</span>
        <h2 style="margin:14px 0 4px;font-size:24px;color:#f0f6fc;text-transform:uppercase;letter-spacing:0.02em;">{inc.get('type','event')}</h2>
        <p style="margin:0;color:#8b949e;font-size:14px;line-height:1.55;">{inc.get('description') or 'Anomaly detected by AI surveillance pipeline.'}</p>
      </td></tr>
      <tr><td style="padding:0 24px 24px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-top:1px solid #1f2730;font-family:'Courier New',monospace;font-size:12px;">
          <tr><td style="padding:10px 0;color:#8b949e;width:40%;">CAMERA</td><td style="padding:10px 0;color:#f0f6fc;">{inc.get('camera_name','—')}</td></tr>
          <tr><td style="padding:10px 0;color:#8b949e;border-top:1px solid #1f2730;">CONFIDENCE</td><td style="padding:10px 0;color:#f0f6fc;border-top:1px solid #1f2730;">{confidence_pct}</td></tr>
          <tr><td style="padding:10px 0;color:#8b949e;border-top:1px solid #1f2730;">DETECTED AT</td><td style="padding:10px 0;color:#f0f6fc;border-top:1px solid #1f2730;">{inc.get('detected_at','—')}</td></tr>
          <tr><td style="padding:10px 0;color:#8b949e;border-top:1px solid #1f2730;">INCIDENT ID</td><td style="padding:10px 0;color:#f0f6fc;border-top:1px solid #1f2730;">{inc.get('id','—')}</td></tr>
        </table>
      </td></tr>
      <tr><td style="padding:14px 24px;background:#0d1117;border-top:1px solid #1f2730;font-size:11px;color:#8b949e;font-family:'Courier New',monospace;letter-spacing:0.1em;">
        review · resolve incident in your sentinel ops console
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>"""


async def _send_alert_email(inc: dict, recipients: List[str]):
    """Fire-and-forget: send the alert via Resend in a thread."""
    if not RESEND_API_KEY or not recipients:
        return
    sev = inc.get("severity", "?").upper()
    typ = inc.get("type", "event").upper()
    cam = inc.get("camera_name", "Unknown")
    params = {
        "from": SENDER_EMAIL,
        "to": recipients,
        "subject": f"[SENTINEL · {sev}] {typ} detected on {cam}",
        "html": _build_alert_html(inc),
    }
    try:
        result = await asyncio.to_thread(resend.Emails.send, params)
        logging.getLogger(__name__).info(
            "Alert email sent: id=%s severity=%s recipients=%d",
            (result or {}).get("id"), sev, len(recipients),
        )
    except Exception as e:
        logging.getLogger(__name__).error("Failed to send alert email: %s", e)


async def _resolve_alert_recipients() -> List[str]:
    """Recipient list = ALERT_RECIPIENT_EMAIL (if set) plus all admin users."""
    recipients = set()
    if ALERT_RECIPIENT_EMAIL:
        recipients.add(ALERT_RECIPIENT_EMAIL)
    cursor = db.users.find({"role": "admin"}, {"_id": 0, "email": 1})
    async for u in cursor:
        if u.get("email"):
            recipients.add(u["email"])
    return list(recipients)


def get_jwt_secret() -> str:
    return os.environ["JWT_SECRET"]


def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def verify_password(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode(), h.encode())
    except Exception:
        return False


def create_access_token(uid: str, email: str) -> str:
    payload = {
        "sub": uid,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=12),
        "type": "access",
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGO)


# ---- Models ----
class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    name: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    role: str


class CameraIn(BaseModel):
    name: str
    location: str
    type: Literal["webcam", "mock"] = "mock"
    image_url: Optional[str] = None
    status: Literal["online", "offline"] = "online"


class Camera(CameraIn):
    id: str
    created_at: str


class IncidentIn(BaseModel):
    camera_id: str
    camera_name: str
    type: str  # person, vehicle, motion, fire, intrusion, crowd
    severity: Literal["low", "medium", "high", "critical"]
    confidence: float = 0.0
    snapshot_url: Optional[str] = None
    description: Optional[str] = None


class Incident(IncidentIn):
    id: str
    detected_at: str
    resolved: bool = False
    resolved_at: Optional[str] = None


class Recording(BaseModel):
    id: str
    camera_id: str
    camera_name: str
    started_at: str
    duration_sec: int
    size_mb: float
    thumbnail_url: Optional[str] = None
    encrypted: bool = False
    anomaly_count: int = 0
    mime_type: Optional[str] = None
    sha256: Optional[str] = None
    has_file: bool = False


class Notification(BaseModel):
    id: str
    title: str
    body: str
    severity: Literal["info", "low", "medium", "high", "critical"]
    created_at: str
    read: bool = False


# ---- Auth dep ----
async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        h = request.headers.get("Authorization", "")
        if h.startswith("Bearer "):
            token = h[7:]
    if not token:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGO])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(401, "User not found")
    return user


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---- Auth routes ----
@api.post("/auth/register", response_model=UserOut)
async def register(payload: RegisterIn, response: Response):
    email = payload.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "Email already registered")
    user = {
        "id": str(uuid.uuid4()),
        "email": email,
        "name": payload.name,
        "role": "operator",
        "password_hash": hash_password(payload.password),
        "created_at": now_iso(),
    }
    await db.users.insert_one(user)
    token = create_access_token(user["id"], email)
    response.set_cookie("access_token", token, httponly=True, samesite="lax", max_age=43200, path="/")
    return UserOut(id=user["id"], email=email, name=user["name"], role=user["role"])


@api.post("/auth/login", response_model=UserOut)
async def login(payload: LoginIn, response: Response):
    email = payload.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    token = create_access_token(user["id"], email)
    response.set_cookie("access_token", token, httponly=True, samesite="lax", max_age=43200, path="/")
    return UserOut(id=user["id"], email=email, name=user["name"], role=user["role"])


@api.post("/auth/logout")
async def logout(response: Response, _user=Depends(get_current_user)):
    response.delete_cookie("access_token", path="/")
    return {"ok": True}


@api.get("/auth/me", response_model=UserOut)
async def me(user=Depends(get_current_user)):
    return UserOut(id=user["id"], email=user["email"], name=user["name"], role=user["role"])


# ---- Cameras ----
@api.get("/cameras", response_model=List[Camera])
async def list_cameras(_user=Depends(get_current_user)):
    docs = await db.cameras.find({}, {"_id": 0}).sort("created_at", 1).to_list(500)
    return docs


@api.post("/cameras", response_model=Camera)
async def add_camera(payload: CameraIn, _user=Depends(get_current_user)):
    cam = {**payload.model_dump(), "id": str(uuid.uuid4()), "created_at": now_iso()}
    await db.cameras.insert_one(cam.copy())
    cam.pop("_id", None)
    return cam


@api.delete("/cameras/{cam_id}")
async def delete_camera(cam_id: str, _user=Depends(get_current_user)):
    res = await db.cameras.delete_one({"id": cam_id})
    if res.deleted_count == 0:
        raise HTTPException(404, "Camera not found")
    return {"ok": True}


@api.patch("/cameras/{cam_id}", response_model=Camera)
async def update_camera(cam_id: str, payload: CameraIn, _user=Depends(get_current_user)):
    await db.cameras.update_one({"id": cam_id}, {"$set": payload.model_dump()})
    cam = await db.cameras.find_one({"id": cam_id}, {"_id": 0})
    if not cam:
        raise HTTPException(404, "Camera not found")
    return cam


# ---- Incidents ----
@api.get("/incidents", response_model=List[Incident])
async def list_incidents(limit: int = 100, _user=Depends(get_current_user)):
    docs = await db.incidents.find({}, {"_id": 0}).sort("detected_at", -1).to_list(limit)
    return docs


@api.post("/incidents", response_model=Incident)
async def create_incident(
    payload: IncidentIn,
    background: BackgroundTasks,
    _user=Depends(get_current_user),
):
    inc = {
        **payload.model_dump(),
        "id": str(uuid.uuid4()),
        "detected_at": now_iso(),
        "resolved": False,
        "resolved_at": None,
    }
    await db.incidents.insert_one(inc.copy())
    # also create notification
    note = {
        "id": str(uuid.uuid4()),
        "title": f"{payload.severity.upper()} · {payload.type} detected",
        "body": f"{payload.camera_name} — {payload.description or 'AI detected anomaly'}",
        "severity": payload.severity,
        "created_at": now_iso(),
        "read": False,
    }
    await db.notifications.insert_one(note.copy())

    # Email alert when severity meets threshold and Resend is configured
    sev_rank = SEVERITY_RANK.get(payload.severity, 0)
    if sev_rank >= ALERT_MIN_RANK and RESEND_API_KEY:
        recipients = await _resolve_alert_recipients()
        if recipients:
            background.add_task(_send_alert_email, inc.copy(), recipients)

    inc.pop("_id", None)
    return inc


@api.post("/incidents/{inc_id}/resolve", response_model=Incident)
async def resolve_incident(inc_id: str, _user=Depends(get_current_user)):
    await db.incidents.update_one(
        {"id": inc_id}, {"$set": {"resolved": True, "resolved_at": now_iso()}}
    )
    inc = await db.incidents.find_one({"id": inc_id}, {"_id": 0})
    if not inc:
        raise HTTPException(404, "Incident not found")
    return inc


# ---- Recordings ----
@api.get("/recordings", response_model=List[Recording])
async def list_recordings(_user=Depends(get_current_user)):
    return await db.recordings.find({}, {"_id": 0}).sort("started_at", -1).to_list(200)


@api.post("/recordings/upload", response_model=Recording)
async def upload_recording(
    file: UploadFile = File(...),
    camera_name: str = Form("Uploaded video"),
    duration_sec: int = Form(0),
    anomaly_count: int = Form(0),
    anomalies_json: str = Form("[]"),
    _user=Depends(get_current_user),
):
    """Encrypt an uploaded video at rest with Fernet (AES-128-CBC + HMAC) and
    store metadata in MongoDB. The file bytes never touch disk in plaintext."""
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "Empty upload")
    rec_id = str(uuid.uuid4())
    digest = hashlib.sha256(raw).hexdigest()
    encrypted = _FERNET.encrypt(raw)
    out_path = RECORDINGS_DIR / f"{rec_id}.enc"
    with open(out_path, "wb") as f:
        f.write(encrypted)
    try:
        anomalies_summary = _json.loads(anomalies_json)
        if not isinstance(anomalies_summary, list):
            anomalies_summary = []
    except Exception:
        anomalies_summary = []

    doc = {
        "id": rec_id,
        "camera_id": "video-upload",
        "camera_name": camera_name,
        "started_at": now_iso(),
        "duration_sec": int(duration_sec or 0),
        "size_mb": round(len(raw) / (1024 * 1024), 2),
        "thumbnail_url": None,
        "encrypted": True,
        "anomaly_count": int(anomaly_count or 0),
        "mime_type": file.content_type or "video/mp4",
        "sha256": digest,
        "has_file": True,
        "anomalies_summary": anomalies_summary,
        "encrypted_path": str(out_path),
        "encrypted_size": len(encrypted),
    }
    await db.recordings.insert_one(doc.copy())
    return {k: v for k, v in doc.items() if k in Recording.model_fields}


@api.get("/recordings/{rec_id}/download")
async def download_recording(rec_id: str, _user=Depends(get_current_user)):
    rec = await db.recordings.find_one({"id": rec_id}, {"_id": 0})
    if not rec:
        raise HTTPException(404, "Recording not found")
    path = rec.get("encrypted_path")
    if not path or not _Path(path).exists():
        raise HTTPException(404, "Encrypted blob missing")
    with open(path, "rb") as f:
        encrypted = f.read()
    try:
        plain = _FERNET.decrypt(encrypted)
    except InvalidToken:
        raise HTTPException(500, "Decryption failed - key mismatch or tampered file")

    def _iter():
        chunk = 64 * 1024
        for i in range(0, len(plain), chunk):
            yield plain[i : i + chunk]

    return StreamingResponse(
        _iter(),
        media_type=rec.get("mime_type", "video/mp4"),
        headers={"Content-Length": str(len(plain))},
    )


@api.delete("/recordings/{rec_id}")
async def delete_recording(rec_id: str, _user=Depends(get_current_user)):
    rec = await db.recordings.find_one({"id": rec_id})
    if not rec:
        raise HTTPException(404, "Not found")
    path = rec.get("encrypted_path")
    if path:
        try:
            _Path(path).unlink(missing_ok=True)
        except Exception:
            pass
    await db.recordings.delete_one({"id": rec_id})
    return {"ok": True}


# ---- Notifications ----
@api.get("/notifications", response_model=List[Notification])
async def list_notifications(_user=Depends(get_current_user)):
    return await db.notifications.find({}, {"_id": 0}).sort("created_at", -1).to_list(50)


@api.post("/notifications/{nid}/read")
async def mark_read(nid: str, _user=Depends(get_current_user)):
    await db.notifications.update_one({"id": nid}, {"$set": {"read": True}})
    return {"ok": True}


@api.post("/notifications/read-all")
async def mark_all_read(_user=Depends(get_current_user)):
    await db.notifications.update_many({}, {"$set": {"read": True}})
    return {"ok": True}


# ---- Analytics ----
@api.get("/analytics/summary")
async def analytics_summary(_user=Depends(get_current_user)):
    total = await db.incidents.count_documents({})
    unresolved = await db.incidents.count_documents({"resolved": False})
    cams = await db.cameras.count_documents({})
    online = await db.cameras.count_documents({"status": "online"})
    by_severity = {}
    for s in ["low", "medium", "high", "critical"]:
        by_severity[s] = await db.incidents.count_documents({"severity": s})

    # Last 7 days timeline
    timeline = []
    today = datetime.now(timezone.utc).date()
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        start = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc).isoformat()
        end = datetime.combine(day, datetime.max.time(), tzinfo=timezone.utc).isoformat()
        count = await db.incidents.count_documents(
            {"detected_at": {"$gte": start, "$lte": end}}
        )
        timeline.append({"date": day.isoformat(), "count": count})

    # By type
    pipeline = [{"$group": {"_id": "$type", "count": {"$sum": 1}}}]
    by_type = []
    async for d in db.incidents.aggregate(pipeline):
        by_type.append({"type": d["_id"], "count": d["count"]})

    # Hourly heatmap (last 24h)
    hourly = [{"hour": h, "count": 0} for h in range(24)]
    cursor = db.incidents.find({}, {"_id": 0, "detected_at": 1})
    async for d in cursor:
        try:
            h = datetime.fromisoformat(d["detected_at"]).hour
            hourly[h]["count"] += 1
        except Exception:
            pass

    return {
        "total_incidents": total,
        "unresolved": unresolved,
        "cameras_total": cams,
        "cameras_online": online,
        "by_severity": by_severity,
        "by_type": by_type,
        "timeline_7d": timeline,
        "hourly": hourly,
    }


# ---- Email alerts (admin) ----
@api.get("/alerts/email/status")
async def alerts_email_status(_user=Depends(get_current_user)):
    return {
        "configured": bool(RESEND_API_KEY),
        "sender": SENDER_EMAIL,
        "min_severity": os.environ.get("ALERT_MIN_SEVERITY", "medium"),
        "default_recipient": ALERT_RECIPIENT_EMAIL or None,
    }


class EmailTestIn(BaseModel):
    recipient: EmailStr


@api.post("/alerts/email/test")
async def alerts_email_test(payload: EmailTestIn, _user=Depends(get_current_user)):
    if not RESEND_API_KEY:
        raise HTTPException(400, "RESEND_API_KEY is not configured in backend/.env")
    sample_inc = {
        "id": "test-" + str(uuid.uuid4())[:8],
        "type": "fire",
        "severity": "high",
        "camera_name": "CAM-TEST · Sentinel Console",
        "confidence": 0.92,
        "description": "This is a test alert from your Sentinel deployment. If you received this, email alerts are working.",
        "detected_at": now_iso(),
    }
    try:
        await _send_alert_email(sample_inc, [payload.recipient])
    except Exception as e:
        raise HTTPException(500, f"Send failed: {e}")
    return {"ok": True, "sent_to": payload.recipient}


# ---- Health ----
@api.get("/")
async def root():
    return {"service": "Sentinel Surveillance API", "ok": True}


app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# ---- Seeding ----
async def seed():
    await db.users.create_index("email", unique=True)
    await db.cameras.create_index("id", unique=True)
    await db.incidents.create_index("id", unique=True)

    admin_email = os.environ.get("ADMIN_EMAIL", "admin@sentinel.io").lower()
    admin_pass = os.environ.get("ADMIN_PASSWORD", "admin123")
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "email": admin_email,
            "name": "Sentinel Admin",
            "role": "admin",
            "password_hash": hash_password(admin_pass),
            "created_at": now_iso(),
        })
        logger.info("Seeded admin user: %s", admin_email)
    elif not verify_password(admin_pass, existing["password_hash"]):
        await db.users.update_one(
            {"email": admin_email},
            {"$set": {"password_hash": hash_password(admin_pass)}},
        )

    if await db.cameras.count_documents({}) == 0:
        cams = [
            {"id": str(uuid.uuid4()), "name": "CAM-01 · Entry Lobby", "location": "Building A · Floor 1",
             "type": "webcam", "image_url": None, "status": "online", "created_at": now_iso()},
            {"id": str(uuid.uuid4()), "name": "CAM-02 · Office Lobby", "location": "Building A · Floor 2",
             "type": "mock",
             "image_url": "https://images.unsplash.com/photo-1749310726959-d8fccfef7ee4?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzZ8MHwxfHNlYXJjaHwxfHxvZmZpY2UlMjBsb2JieSUyMHNlY3VyaXR5JTIwY2FtZXJhfGVufDB8fHx8MTc3NzE2ODExNnww&ixlib=rb-4.1.0&q=85",
             "status": "online", "created_at": now_iso()},
            {"id": str(uuid.uuid4()), "name": "CAM-03 · Street View", "location": "North Perimeter",
             "type": "mock",
             "image_url": "https://images.unsplash.com/photo-1761211798396-a0716cb27505?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2Mzl8MHwxfHNlYXJjaHwyfHx1cmJhbiUyMHN0cmVldCUyMHNlY3VyaXR5JTIwY2FtZXJhfGVufDB8fHx8MTc3NzE2ODExNnww&ixlib=rb-4.1.0&q=85",
             "status": "online", "created_at": now_iso()},
            {"id": str(uuid.uuid4()), "name": "CAM-04 · Parking Lot", "location": "South Lot · Sector B",
             "type": "mock",
             "image_url": "https://images.unsplash.com/photo-1653750366046-289780bd8125?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA2MjJ8MHwxfHNlYXJjaHwxfHxwYXJraW5nJTIwbG90JTIwc2VjdXJpdHklMjBjYW1lcmF8ZW58MHx8fHwxNzc3MTY4MTE2fDA&ixlib=rb-4.1.0&q=85",
             "status": "offline", "created_at": now_iso()},
        ]
        await db.cameras.insert_many([c.copy() for c in cams])

        # Seed incidents using `secrets` so the linter doesn't flag the
        # `random` module as cryptographically insecure (this is purely
        # demo seed data, but `secrets` is an equivalent, safe choice).
        types = ["person", "vehicle", "motion", "intrusion", "crowd"]
        sevs = ["low", "medium", "high", "critical"]
        sample = []
        import secrets
        for i in range(24):
            cam = secrets.choice(cams)
            t = secrets.choice(types)
            s = secrets.choice(sevs)
            hours_back = secrets.randbelow(145)  # 0..144
            ts = (datetime.now(timezone.utc) - timedelta(hours=hours_back)).isoformat()
            confidence = round(0.6 + secrets.randbelow(40) / 100, 2)  # 0.60..0.99
            sample.append({
                "id": str(uuid.uuid4()),
                "camera_id": cam["id"],
                "camera_name": cam["name"],
                "type": t,
                "severity": s,
                "confidence": confidence,
                "snapshot_url": cam.get("image_url"),
                "description": f"{t.title()} detected in {cam['location']}",
                "detected_at": ts,
                "resolved": secrets.randbelow(2) == 0,
                "resolved_at": None,
            })
        await db.incidents.insert_many(sample)

        # Seed recordings
        recs = []
        for cam in cams:
            for i in range(3):
                recs.append({
                    "id": str(uuid.uuid4()),
                    "camera_id": cam["id"],
                    "camera_name": cam["name"],
                    "started_at": (datetime.now(timezone.utc) - timedelta(hours=i * 6)).isoformat(),
                    "duration_sec": 600 + i * 120,
                    "size_mb": round(80 + i * 14.5, 1),
                    "thumbnail_url": cam.get("image_url"),
                })
        await db.recordings.insert_many(recs)

        # Seed a few notifications
        for inc in sample[:5]:
            await db.notifications.insert_one({
                "id": str(uuid.uuid4()),
                "title": f"{inc['severity'].upper()} · {inc['type']} detected",
                "body": f"{inc['camera_name']} — {inc['description']}",
                "severity": inc["severity"],
                "created_at": inc["detected_at"],
                "read": False,
            })


@app.on_event("startup")
async def on_start():
    await seed()


@app.on_event("shutdown")
async def on_stop():
    client.close()
