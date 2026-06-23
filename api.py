"""
DrishtiVia 2.0 — FastAPI backend
Run: uvicorn api:app --reload --port 8000

IMPORTANT: This file imports ONLY from detect_core.py (zero Streamlit dependency).
Never import from app.py — it has module-level st.tabs() / st.set_page_config()
calls that crash immediately outside a Streamlit server.
"""
import os, base64, tempfile, sqlite3, re, time, json, uuid, asyncio, threading
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, deque

import cv2
import numpy as np
import requests as http_requests
from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Header, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from pydantic import BaseModel

# Load .env if present (python-dotenv optional)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── detect_core: pure Python, no Streamlit ────────────────────────────────────
from detect_core import (
    preprocess,
    detect_violations,
    annotate,
    classify_plate_category,
    reset_tracking,
    reset_id_map,
)

# ── config from environment ───────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DB_PATH  = Path(os.getenv("DB_PATH",  str(BASE_DIR / "evidence_store" / "violations.db")))
SNAP_DIR = Path(os.getenv("SNAP_DIR", str(BASE_DIR / "evidence_store" / "snapshots")))
SNAP_DIR.mkdir(parents=True, exist_ok=True)

HELMET_PATH    = Path(os.getenv("HELMET_MODEL",    str(BASE_DIR / "runs/detect/runs/detect/helmet_v2/weights/best.pt")))
SEATBELT_PATH  = Path(os.getenv("SEATBELT_MODEL",  str(BASE_DIR / "runs/detect/runs/seatbelt_train/violavision_seatbelt_v1-2/weights/best.pt")))
WRONGSIDE_PATH = Path(os.getenv("WRONGSIDE_MODEL", str(BASE_DIR / "runs/detect/runs/wrongside_train/violavision_wrongside_v1/weights/best.pt")))

# API key auth — set API_KEY env var to enable; leave blank to run without auth (dev/demo)
_API_KEY = os.getenv("API_KEY", "").strip()

# CORS — comma-separated list of allowed origins
_CORS_ORIGINS = [o.strip() for o in os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",") if o.strip()]

# File size limits
MAX_IMAGE_BYTES = int(os.getenv("MAX_IMAGE_MB", "10"))  * 1024 * 1024
MAX_VIDEO_BYTES = int(os.getenv("MAX_VIDEO_MB", "200")) * 1024 * 1024

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(title="DrishtiVia API", version="2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Auth dependency ───────────────────────────────────────────────────────────
def require_auth(x_api_key: str = Header(default="")):
    """Enforce API key if one is configured. Skipped when API_KEY env var is empty."""
    if _API_KEY and x_api_key != _API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Api-Key header")

# ── Simple in-memory rate limiter for expensive endpoints ─────────────────────
_rate_buckets: dict = defaultdict(list)
_rate_lock = threading.Lock()

def _check_rate(request: Request, max_per_minute: int):
    ip  = request.client.host if request.client else "unknown"
    key = f"{ip}:{request.url.path}"
    now = time.time()
    with _rate_lock:
        _rate_buckets[key] = [t for t in _rate_buckets[key] if now - t < 60]
        if len(_rate_buckets[key]) >= max_per_minute:
            raise HTTPException(429, "Rate limit exceeded — try again in a minute")
        _rate_buckets[key].append(now)

# ── Video session store: session_id -> (tmp_file_path, created_timestamp) ─────
_video_sessions: dict[str, tuple[str, float]] = {}

def _get_session_path(sid: str) -> str:
    entry = _video_sessions.get(sid)
    if not entry:
        raise HTTPException(404, "Session not found or expired — re-upload the video")
    path, _ = entry
    if not Path(path).exists():
        raise HTTPException(404, "Session file missing — re-upload the video")
    return path

def _cleanup_stale_sessions():
    """Background thread: delete temp video files older than 30 minutes."""
    while True:
        time.sleep(300)
        now  = time.time()
        stale = [sid for sid, (_, ts) in list(_video_sessions.items()) if now - ts > 1800]
        for sid in stale:
            entry = _video_sessions.pop(sid, None)
            if entry:
                try:
                    Path(entry[0]).unlink(missing_ok=True)
                except Exception:
                    pass

# ── lazy model cache ──────────────────────────────────────────────────────────
_models: dict = {}

def _yolo():
    if "base" not in _models:
        from ultralytics import YOLO
        _models["base"] = YOLO(str(BASE_DIR / "yolov8s.pt"))
    return _models["base"]

def _helmet():
    if "helmet" not in _models:
        if HELMET_PATH.exists():
            from ultralytics import YOLO
            _models["helmet"] = YOLO(str(HELMET_PATH))
        else:
            _models["helmet"] = None
    return _models["helmet"]

def _seatbelt():
    if "seatbelt" not in _models:
        if SEATBELT_PATH.exists():
            from ultralytics import YOLO
            _models["seatbelt"] = YOLO(str(SEATBELT_PATH))
        else:
            _models["seatbelt"] = None
    return _models["seatbelt"]

def _wrongside():
    if "wrongside" not in _models:
        if WRONGSIDE_PATH.exists():
            from ultralytics import YOLO
            _models["wrongside"] = YOLO(str(WRONGSIDE_PATH))
        else:
            _models["wrongside"] = None
    return _models["wrongside"]

def _ocr():
    if "ocr" not in _models:
        import easyocr
        _models["ocr"] = easyocr.Reader(["en"], gpu=False)
    return _models["ocr"]

# ── DB ─────────────────────────────────────────────────────────────────────────
def _db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con

def _row_to_dict(row) -> dict:
    d = dict(row)
    d["severity"] = d.get("priority_level") or "LOW"
    return d

# ── startup: DB indexes + signing key + session cleanup thread ─────────────────
@app.on_event("startup")
def _startup():
    # Ensure DB indexes exist for fast queries
    con = _db()
    con.execute("CREATE INDEX IF NOT EXISTS idx_plate    ON violations(plate_number)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_ts       ON violations(timestamp)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_camera   ON violations(camera_id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_action   ON violations(operator_action)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_priority ON violations(priority_level)")
    con.commit()
    con.close()

    # Auto-generate signing key if missing
    key_path = BASE_DIR / "models" / "signing_key.pem"
    if not key_path.exists():
        try:
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.primitives import serialization
            key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            key_path.parent.mkdir(parents=True, exist_ok=True)
            key_path.write_bytes(key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption(),
            ))
        except ImportError:
            pass  # cryptography package not installed — signing unavailable

    # Start background cleanup thread for stale video sessions
    t = threading.Thread(target=_cleanup_stale_sessions, daemon=True)
    t.start()

    # Pre-load all models at startup so the first video request doesn't cold-start
    # PyTorch + YOLO weights (which causes the "Connecting..." delay of 5-15s)
    def _warm_models():
        try:
            _yolo()
            _helmet()
            _seatbelt()
            _wrongside()
        except Exception:
            pass
    threading.Thread(target=_warm_models, daemon=True).start()

# ── image helpers ──────────────────────────────────────────────────────────────
_PLATE_RE = re.compile(r"^[A-Z]{2}[0-9]{2}[A-Z]{1,3}[0-9]{3,4}$")

def _bgr_from_bytes(data: bytes) -> np.ndarray:
    arr = np.frombuffer(data, np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)

def _bgr_to_b64(bgr: np.ndarray) -> str:
    _, buf = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, 88])
    return base64.b64encode(buf).decode()

def _extract_plate(frame: np.ndarray) -> str:
    try:
        ocr  = _ocr()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        for (_, text, conf) in ocr.readtext(thresh):
            cleaned = re.sub(r"[^A-Z0-9]", "", text.upper())
            if _PLATE_RE.match(cleaned) and conf > 0.4:
                return cleaned
    except Exception:
        pass
    return "UNREADABLE"

def _clean_viols(viols: list) -> list:
    """Strip non-JSON-serialisable fields."""
    out = []
    for v in viols:
        c = {k: val for k, val in v.items() if k != "geo_features"}
        if "bbox" in c:
            c["bbox"] = [float(x) for x in c["bbox"]]
        out.append(c)
    return out

def _add_vehicle_category(viols: list, frame: np.ndarray) -> list:
    for v in viols:
        try:
            x1, y1, x2, y2 = [int(c) for c in v["bbox"]]
            crop = frame[max(0,y1):y2, max(0,x1):x2]
            v["vehicle_category"] = classify_plate_category(crop)
        except Exception:
            v["vehicle_category"] = "Unknown"
    return viols

# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

# ── Health (public — no auth required) ───────────────────────────────────────
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "db_connected": DB_PATH.exists(),
        "models": {
            "base_yolo": True,
            "helmet":    HELMET_PATH.exists(),
            "seatbelt":  SEATBELT_PATH.exists(),
            "wrongside": WRONGSIDE_PATH.exists(),
        },
        "active_count": 1 + sum([HELMET_PATH.exists(), SEATBELT_PATH.exists(), WRONGSIDE_PATH.exists()]),
    }

# ── Stats ─────────────────────────────────────────────────────────────────────
@app.get("/api/stats", dependencies=[Depends(require_auth)])
def stats():
    con = _db(); cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM violations")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM violations WHERE operator_action IS NULL")
    pending = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT plate_number) FROM violations WHERE plate_number!='UNREADABLE'")
    plates = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM violations WHERE UPPER(operator_action)='CONFIRMED'")
    confirmed = cur.fetchone()[0]
    cur.execute("SELECT violation_type, COUNT(*) as cnt FROM violations GROUP BY violation_type ORDER BY cnt DESC LIMIT 5")
    top_types = [{"type": r[0], "count": r[1]} for r in cur.fetchall()]
    cur.execute("SELECT camera_id, COUNT(*) as cnt FROM violations GROUP BY camera_id ORDER BY cnt DESC")
    by_camera = [{"camera": r[0], "count": r[1]} for r in cur.fetchall()]
    con.close()
    return {"total": total, "pending": pending, "plates": plates,
            "confirmed": confirmed, "top_types": top_types, "by_camera": by_camera}

# ── Violations list ───────────────────────────────────────────────────────────
@app.get("/api/violations", dependencies=[Depends(require_auth)])
def violations(
    limit:          int  = 100,
    offset:         int  = 0,
    status:         str  = "all",
    violation_type: str  = "",
    severity:       str  = "",
    plate:          str  = "",
    from_ts:        float = 0,
    to_ts:          float = 0,
    sort:           str  = "newest",
):
    con = _db(); cur = con.cursor()
    where_clauses = []
    params: list = []

    if status == "pending":
        where_clauses.append("operator_action IS NULL")
    elif status == "confirmed":
        where_clauses.append("UPPER(operator_action)='CONFIRMED'")
    elif status == "escalated":
        where_clauses.append("UPPER(operator_action)='ESCALATED'")

    if violation_type:
        where_clauses.append("UPPER(violation_type) LIKE ?")
        params.append(f"%{violation_type.upper()}%")
    if severity:
        sevs = [s.strip().upper() for s in severity.split(",") if s.strip()]
        where_clauses.append(f"UPPER(priority_level) IN ({','.join('?' for _ in sevs)})")
        params.extend(sevs)
    if plate:
        where_clauses.append("UPPER(plate_number) LIKE ?")
        params.append(f"%{plate.upper()}%")
    if from_ts:
        where_clauses.append("timestamp >= ?")
        params.append(from_ts)
    if to_ts:
        where_clauses.append("timestamp <= ?")
        params.append(to_ts)

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    order_sql = "ORDER BY timestamp ASC" if sort == "oldest" else "ORDER BY timestamp DESC"

    cur.execute(f"SELECT COUNT(*) FROM violations {where_sql}", params)
    total = cur.fetchone()[0]

    cur.execute(f"SELECT * FROM violations {where_sql} {order_sql} LIMIT ? OFFSET ?",
                params + [limit, offset])
    rows = [_row_to_dict(r) for r in cur.fetchall()]
    con.close()
    return {"violations": rows, "count": len(rows), "total": total}

# ── Search ────────────────────────────────────────────────────────────────────
@app.get("/api/search", dependencies=[Depends(require_auth)])
def search(q: str = Query(""), limit: int = 50):
    if not q.strip():
        return {"results": [], "count": 0}
    con = _db(); cur = con.cursor()
    pat = f"%{q.upper()}%"
    cur.execute("""
        SELECT * FROM violations
        WHERE UPPER(plate_number) LIKE ?
           OR UPPER(violation_type) LIKE ?
           OR UPPER(camera_id) LIKE ?
           OR UPPER(priority_level) LIKE ?
        ORDER BY timestamp DESC LIMIT ?
    """, (pat, pat, pat, pat, limit))
    rows = [_row_to_dict(r) for r in cur.fetchall()]
    con.close()
    return {"results": rows, "count": len(rows)}

# ── Save detected violations to DB ───────────────────────────────────────────
import hashlib

class SaveViolationBody(BaseModel):
    violation_type: str
    confidence:     float
    severity:       str
    camera_id:      str = "Unknown"
    plate_number:   str = "UNREADABLE"
    vehicle_id:     str = ""
    description:    str = ""
    bbox:           list = []

@app.post("/api/violations/save", dependencies=[Depends(require_auth)])
def save_violation(body: SaveViolationBody):
    """Save a single detected violation from the Live Detect page into SQLite."""
    ts      = time.time()
    raw     = f"{body.violation_type}{body.camera_id}{body.plate_number}{ts}"
    ev_hash = hashlib.sha256(raw.encode()).hexdigest()

    PRIORITY_MAP = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
    priority_score = round(
        PRIORITY_MAP.get(body.severity.upper(), 1) * body.confidence * 10, 2
    )

    con = _db()
    _ensure_schema(con)
    con.execute("""
        INSERT INTO violations
            (timestamp, plate_number, violation_type, confidence, priority_level,
             priority_score, camera_id, evidence_hash, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (ts, body.plate_number, body.violation_type, body.confidence,
          body.severity.upper(), priority_score, body.camera_id, ev_hash, body.description))
    con.commit()
    new_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
    con.close()
    return {"ok": True, "id": new_id, "evidence_hash": ev_hash}


def _ensure_schema(con):
    """Create table and add any missing columns without dropping existing data."""
    con.execute("""
        CREATE TABLE IF NOT EXISTS violations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL, plate_number TEXT, violation_type TEXT,
            confidence REAL, priority_score REAL, priority_level TEXT,
            evidence_hash TEXT, camera_id TEXT, operator_action TEXT,
            operator_timestamp REAL, dismissal_reason TEXT, snapshot_path TEXT,
            description TEXT, vehicle_id TEXT, bbox TEXT
        )
    """)
    cur = con.execute("PRAGMA table_info(violations)")
    existing = {r[1] for r in cur.fetchall()}
    for col, typedef in [
        ("description",      "TEXT"),
        ("vehicle_id",       "TEXT"),
        ("bbox",             "TEXT"),
        ("dismissal_reason", "TEXT"),
        ("operator_timestamp", "REAL"),
    ]:
        if col not in existing:
            con.execute(f"ALTER TABLE violations ADD COLUMN {col} {typedef}")


def _persist_violation(viol: dict, frame_bgr, camera_id: str,
                       plate: str = "UNREADABLE") -> tuple:
    """
    Save one confirmed violation + evidence snapshots (full frame + vehicle
    crop) to SQLite. Returns the evidence hash.
    """
    ts      = time.time()
    vtype   = viol.get("type", "Unknown")
    conf    = float(viol.get("confidence", 0) or 0)
    sev     = str(viol.get("severity", "MEDIUM")).upper()
    ev_hash = hashlib.sha256(f"{vtype}{camera_id}{plate}{ts}".encode()).hexdigest()
    h16     = ev_hash[:16]

    snap_full = SNAP_DIR / f"{h16}_full.jpg"
    snap_crop = SNAP_DIR / f"{h16}_crop.jpg"
    try:
        if frame_bgr is not None:
            jpg_params = [cv2.IMWRITE_JPEG_QUALITY, 92]
            cv2.imwrite(str(snap_full), frame_bgr, jpg_params)
            # Use crop_bbox if provided, else fall back to bbox
            crop_ref = viol.get("crop_bbox") or viol.get("bbox")
            if crop_ref and len(crop_ref) == 4:
                x1, y1, x2, y2 = [max(0, int(c)) for c in crop_ref]
                ih, iw = frame_bgr.shape[:2]
                x2, y2 = min(x2, iw), min(y2, ih)
                crop = frame_bgr[y1:y2, x1:x2]
                if crop.size > 0:
                    # Upscale tiny crops to at least 400px wide so they're
                    # not blurry when displayed in the evidence modal
                    cw = crop.shape[1]
                    if cw < 400 and cw > 0:
                        scale = 400 / cw
                        crop = cv2.resize(crop, None, fx=scale, fy=scale,
                                          interpolation=cv2.INTER_LANCZOS4)
                    cv2.imwrite(str(snap_crop), crop, jpg_params)
    except Exception:
        pass

    PRIORITY_MAP   = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
    priority_score = round(PRIORITY_MAP.get(sev, 1) * conf * 10, 2)

    con = _db()
    _ensure_schema(con)
    con.execute("""
        INSERT INTO violations
            (timestamp, plate_number, violation_type, confidence,
             priority_level, priority_score, camera_id, evidence_hash,
             snapshot_path, description, vehicle_id, bbox)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (ts, plate, vtype, conf, sev, priority_score, camera_id, ev_hash,
          str(snap_full), viol.get("description", ""),
          viol.get("vehicle_id", ""), str(viol.get("bbox", []))))
    con.commit()
    db_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
    con.close()
    return ev_hash, db_id

# ── Violation action ──────────────────────────────────────────────────────────
class ActionBody(BaseModel):
    action: str

@app.post("/api/violations/{vid}/action", dependencies=[Depends(require_auth)])
def violation_action(vid: int, body: ActionBody):
    con = _db()
    con.execute("UPDATE violations SET operator_action=? WHERE id=?",
                (body.action.upper(), vid))
    con.commit(); con.close()
    return {"ok": True, "id": vid, "action": body.action}

# ── Detect image ──────────────────────────────────────────────────────────────
@app.post("/api/detect/image", dependencies=[Depends(require_auth)])
async def detect_image(
    request: Request,
    file: UploadFile = File(...),
    stop_line_y: int = 400,
    signal_red: bool = False,
    stopline_enabled: bool = False,
    scene_type: str = "Junction",
    wrong_side_present: bool = False,
    flow_direction: str = "Left -> Right",
    preprocessing: bool = True,
):
    _check_rate(request, max_per_minute=30)
    data = await file.read()
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(413, f"Image exceeds {MAX_IMAGE_BYTES // 1024 // 1024}MB limit")

    frame = _bgr_from_bytes(data)
    if frame is None:
        raise HTTPException(400, "Could not decode image")

    processed = preprocess(frame, preprocessing)
    yolo = _yolo()
    res  = yolo(processed, verbose=False)

    det_result = detect_violations(
        res, stop_line_y, processed.shape[:2],
        frame_bgr=processed,
        helmet_model=_helmet(),
        seatbelt_model=_seatbelt(),
        wrongside_model=_wrongside(),
        signal_red=signal_red,
        stopline_enabled=stopline_enabled,
        scene_type=scene_type,
        wrong_side_present=wrong_side_present,
        flow_direction=flow_direction,
    )
    viols    = det_result["violations"]
    vehicles = det_result["vehicles"]
    _add_vehicle_category(viols, processed)
    annotated = annotate(processed, viols, vehicles=vehicles)
    plate     = _extract_plate(processed)
    clean     = _clean_viols(viols)

    return {
        "violations":    clean,
        "plate":         plate,
        "count":         len(clean),
        "original_b64":  _bgr_to_b64(frame),
        "annotated_b64": _bgr_to_b64(annotated),
    }

# ── Detect video (ByteTrack) ───────────────────────────────────────────────────
@app.post("/api/detect/video", dependencies=[Depends(require_auth)])
async def detect_video(
    request: Request,
    file: UploadFile = File(...),
    stop_line_y: int = 400,
    frame_skip: int = 6,
    max_seconds: int = 60,
    signal_red: bool = False,
    stopline_enabled: bool = False,
    scene_type: str = "Junction",
    wrong_side_present: bool = False,
    flow_direction: str = "Left -> Right",
):
    _check_rate(request, max_per_minute=5)
    data = await file.read()
    if len(data) > MAX_VIDEO_BYTES:
        raise HTTPException(413, f"Video exceeds {MAX_VIDEO_BYTES // 1024 // 1024}MB limit")

    suffix = Path(file.filename or "vid.mp4").suffix or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    reset_tracking(); reset_id_map()
    yolo = _yolo()

    cap        = cv2.VideoCapture(tmp_path)
    fps        = cap.get(cv2.CAP_PROP_FPS) or 25.0
    max_frames = int(max_seconds * fps)
    frame_count    = 0
    analysed_count = 0

    temporal_counts: dict = defaultdict(int)
    temporal_best:   dict = {}
    confirmed_viols: list = []
    confirmed_types: set  = set()

    try:
        while True:
            ok, raw_frame = cap.read()
            if not ok or frame_count >= max_frames:
                break
            frame_count += 1
            if frame_count % frame_skip != 0:
                continue

            h0, w0 = raw_frame.shape[:2]
            scale_down = min(1.0, 640 / max(w0, 1))
            small = cv2.resize(raw_frame, (int(w0 * scale_down), int(h0 * scale_down))) if scale_down < 1.0 else raw_frame
            processed = preprocess(small, True)
            analysed_count += 1

            res = yolo.track(processed, persist=True, verbose=False)

            det_result = detect_violations(
                res, int(stop_line_y * scale_down), processed.shape[:2],
                frame_bgr=processed,
                helmet_model=_helmet(),
                seatbelt_model=_seatbelt(),
                wrongside_model=_wrongside(),
                signal_red=signal_red,
                stopline_enabled=stopline_enabled,
                scene_type=scene_type,
                wrong_side_present=wrong_side_present,
                flow_direction=flow_direction,
            )
            viols    = det_result["violations"]
            vehicles = det_result["vehicles"]
            _add_vehicle_category(viols, processed)

            for v in viols:
                v["frame"] = frame_count
                vtype = v.get("type", "")
                vid   = v.get("vehicle_id", "unknown")
                conf  = v.get("confidence", 0)
                tkey  = f"{vtype}::{vid}"

                temporal_counts[tkey] += 1
                if tkey not in temporal_best or conf > temporal_best[tkey].get("confidence", 0):
                    temporal_best[tkey] = v

                if tkey not in confirmed_types:
                    if temporal_counts[tkey] >= 2 or conf >= 0.38:
                        c = _clean_viols([v])[0]
                        c["confirmed_at_frame"] = frame_count
                        c["sightings"] = temporal_counts[tkey]
                        confirmed_viols.append(c)
                        confirmed_types.add(tkey)

    finally:
        cap.release()
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass

    for key, v in temporal_best.items():
        vtype = v.get("type", "")
        if vtype not in confirmed_types and temporal_counts.get(key, 0) >= 1:
            c = _clean_viols([v])[0]
            c["note"] = f"Single-frame only (seen {temporal_counts[key]}× — below threshold)"
            confirmed_viols.append(c)
            confirmed_types.add(vtype)

    return {
        "total_frames":    frame_count,
        "frames_analysed": frame_count // max(frame_skip, 1),
        "violations":      confirmed_viols,
        "count":           len(confirmed_viols),
    }

# ── Analytics ─────────────────────────────────────────────────────────────────
@app.get("/api/analytics", dependencies=[Depends(require_auth)])
def analytics(days: int = 7):
    con = _db(); cur = con.cursor()
    since = (datetime.now() - timedelta(days=days)).timestamp()
    cur.execute("""
        SELECT date(datetime(timestamp,'unixepoch')) as day,
               violation_type, COUNT(*) as cnt
        FROM violations WHERE timestamp > ?
        GROUP BY day, violation_type ORDER BY day
    """, (since,))
    rows = cur.fetchall()
    cur.execute("""
        SELECT plate_number, COUNT(*) as cnt,
               GROUP_CONCAT(DISTINCT violation_type) as types
        FROM violations
        WHERE timestamp > ? AND plate_number != 'UNREADABLE' AND LENGTH(plate_number) >= 6
        GROUP BY plate_number HAVING cnt >= 2 ORDER BY cnt DESC LIMIT 10
    """, (since,))
    offenders = [{"plate": r[0], "count": r[1], "types": r[2]} for r in cur.fetchall()]

    cur.execute("""
        SELECT camera_id, COUNT(*) as cnt, AVG(priority_score) as avg_p
        FROM violations GROUP BY camera_id ORDER BY cnt DESC
    """)
    hotspots_raw = cur.fetchall()
    con.close()

    CAMERA_COORDS = {
        "silk_board_junction": [12.9170, 77.6234],
        "silk_board":          [12.9170, 77.6234],
        "kr_circle":           [12.9767, 77.5713],
        "hebbal_flyover":      [13.0450, 77.5970],
        "marathahalli_bridge": [12.9591, 77.7003],
        "whitefield_01":       [12.9698, 77.7500],
    }
    hotspots = []
    for r in hotspots_raw:
        cam = r[0] or "unknown"
        key = cam.lower().replace(" ", "_").replace("-", "_")
        coords = None
        for k, v in CAMERA_COORDS.items():
            if k in key or key in k:
                coords = v
                break
        hotspots.append({
            "camera": cam, "count": r[1],
            "avg_priority": round(r[2] or 0, 1),
            "lat": (coords[0] if coords else 12.9716),
            "lng": (coords[1] if coords else 77.5946),
        })

    by_day: dict = {}
    for row in rows:
        day = row[0] or "unknown"
        if day not in by_day:
            by_day[day] = {}
        by_day[day][row[1]] = row[2]

    return {
        "by_day":           [{"day": d, **vals} for d, vals in sorted(by_day.items())],
        "repeat_offenders": offenders,
        "hotspots":         hotspots,
    }

# ── Knowledge Graph ───────────────────────────────────────────────────────────
@app.get("/api/graph", dependencies=[Depends(require_auth)])
def knowledge_graph(limit: int = 80):
    con = _db(); cur = con.cursor()
    cur.execute("""
        SELECT plate_number, camera_id, violation_type,
               priority_score, priority_level, timestamp
        FROM violations ORDER BY timestamp DESC LIMIT ?
    """, (limit,))
    edges = [dict(r) for r in cur.fetchall()]
    cur.execute("""
        SELECT plate_number, COUNT(*) as cnt,
               GROUP_CONCAT(DISTINCT violation_type) as types
        FROM violations WHERE plate_number != 'UNREADABLE'
        GROUP BY plate_number HAVING cnt >= 2 ORDER BY cnt DESC LIMIT 10
    """)
    offenders = [{"plate": r[0], "count": r[1], "types": r[2]} for r in cur.fetchall()]
    cur.execute("""
        SELECT camera_id, COUNT(*) as cnt, AVG(priority_score) as avg_priority
        FROM violations GROUP BY camera_id ORDER BY cnt DESC
    """)
    hotspots = [{"camera": r[0], "count": r[1], "avg_priority": round(r[2] or 0, 1)} for r in cur.fetchall()]
    con.close()
    return {"edges": edges, "repeat_offenders": offenders, "hotspots": hotspots}

# ── URL / YouTube live stream → SSE ──────────────────────────────────────────
import subprocess, shutil

def _get_ffmpeg() -> str:
    """Return path to ffmpeg — prefer system install, fall back to imageio-ffmpeg bundle."""
    p = shutil.which("ffmpeg")
    if p:
        return p
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        raise HTTPException(500, "ffmpeg not found. Run: pip install imageio-ffmpeg")


def _open_stream_cap(url: str):
    """
    Open a VideoCapture for any URL.
    For YouTube/youtu.be: resolves via yt-dlp (android client, no JS needed)
    then pipes through ffmpeg → OpenCV in real time so nothing is downloaded.
    For RTSP/HLS: opens directly with OpenCV.
    Returns (cap, cleanup_fn).
    """
    ytdlp = shutil.which("yt-dlp")
    is_youtube = "youtube.com" in url or "youtu.be" in url

    if not is_youtube:
        cap = cv2.VideoCapture(url)
        return cap, lambda: None

    if not ytdlp:
        raise HTTPException(400, "yt-dlp not installed. Run: pip install yt-dlp")

    # Step 1: resolve the live HLS URL (android player_client skips JS requirement)
    res = subprocess.run(
        [ytdlp, "--extractor-args", "youtube:player_client=android",
         "-f", "best[height<=480][ext=mp4]/best[height<=480]/best",
         "-g", "--no-playlist", "--quiet", url],
        capture_output=True, text=True, timeout=30
    )
    hls_url = res.stdout.strip().splitlines()[0] if res.stdout.strip() else ""
    if not hls_url:
        raise HTTPException(400, f"yt-dlp could not resolve stream URL: {res.stderr[:200]}")

    # Step 2: pipe HLS → ffmpeg → raw BGR frames
    # Force 640x360 so frame size is always known (nbytes = 640*360*3)
    # -user_agent required: YouTube returns 403 to ffmpeg without a browser UA
    ffmpeg = _get_ffmpeg()
    ff_proc = subprocess.Popen(
        [
            ffmpeg, "-loglevel", "quiet",
            "-user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "-i", hls_url,
            "-f", "rawvideo",
            "-pix_fmt", "bgr24",
            "-vf", "scale=640:360",  # exact size so frame bytes are predictable
            "-r", "10",              # 10 fps — sufficient for CV
            "pipe:1",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    return ff_proc, (640, 360), lambda: ff_proc.terminate()


FFMPEG_W, FFMPEG_H = 640, 360


def _read_ffmpeg_frame(ff_proc):
    """Read one raw BGR frame from an ffmpeg pipe (640x360)."""
    nbytes = FFMPEG_W * FFMPEG_H * 3
    raw = b""
    while len(raw) < nbytes:
        chunk = ff_proc.stdout.read(nbytes - len(raw))
        if not chunk:
            return None
        raw += chunk
    return np.frombuffer(raw, np.uint8).reshape((FFMPEG_H, FFMPEG_W, 3))


@app.get("/api/detect/stream/live", dependencies=[Depends(require_auth)])
async def stream_from_url(
    url:                str,
    stop_line_y:        int  = 400,
    frame_skip:         int  = 4,
    max_seconds:        int  = 60,
    signal_red:         bool = False,
    stopline_enabled:   bool = False,
    scene_type:         str  = "Junction",
    wrong_side_present: bool = False,
    flow_direction:     str  = "Left -> Right",
    camera_id:          str  = "live_stream",
):
    is_youtube = "youtube.com" in url or "youtu.be" in url
    reset_tracking(); reset_id_map()
    yolo = _yolo()

    async def generate():
        ff_proc = None
        cap     = None

        if is_youtube:
            yield f"data: {json.dumps({'status': 'connecting', 'msg': 'Resolving live stream via yt-dlp…'})}\n\n"
            await asyncio.sleep(0)

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, _open_stream_cap, url
            )
        except HTTPException as e:
            yield f"data: {json.dumps({'error': e.detail})}\n\n"
            return
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        # result is either (cap, cleanup) or (ff_proc, (w,h), cleanup)
        use_ffmpeg_pipe = is_youtube
        if use_ffmpeg_pipe:
            ff_proc, (frame_w, frame_h), cleanup = result
        else:
            cap, cleanup = result
            if not cap.isOpened():
                yield f"data: {json.dumps({'error': 'Cannot open stream URL.'})}\n\n"
                return

        if is_youtube:
            yield f"data: {json.dumps({'status': 'live', 'msg': 'Connected — analysing live frames…'})}\n\n"
            await asyncio.sleep(0)

        frame_count    = 0
        analysed_count = 0
        max_frames     = max_seconds * 10 if use_ffmpeg_pipe else int(max_seconds * (cap.get(cv2.CAP_PROP_FPS) or 25))
        temporal_counts: dict = defaultdict(int)
        temporal_best:   dict = {}
        confirmed_viols: list = []
        # Key: "ViolationType::VehicleID" — one entry per (type, vehicle) pair
        confirmed_keys: set   = set()

        try:
            while frame_count < max_frames:
                if use_ffmpeg_pipe:
                    raw_frame = await asyncio.get_event_loop().run_in_executor(
                        None, _read_ffmpeg_frame, ff_proc
                    )
                    if raw_frame is None:
                        break
                else:
                    ok, raw_frame = cap.read()
                    if not ok:
                        break

                frame_count += 1
                if frame_count % frame_skip != 0:
                    continue

                processed = preprocess(raw_frame, True)
                analysed_count += 1

                res = yolo.track(processed, persist=True, verbose=False)
                det_result = detect_violations(
                    res, stop_line_y, processed.shape[:2],
                    frame_bgr=processed,
                    helmet_model=_helmet(), seatbelt_model=_seatbelt(),
                    wrongside_model=_wrongside(),
                    signal_red=signal_red, stopline_enabled=stopline_enabled,
                    scene_type=scene_type, wrong_side_present=wrong_side_present,
                    flow_direction=flow_direction,
                )
                viols    = det_result["violations"]
                vehicles = det_result["vehicles"]
                _add_vehicle_category(viols, processed)

                new_confirmed = []
                for v in viols:
                    v["frame"] = frame_count
                    vtype  = v.get("type", "")
                    vid    = v.get("vehicle_id", "unknown")
                    conf   = v.get("confidence", 0)
                    # Track per (violation_type, vehicle_id) — separate log per vehicle
                    tkey   = f"{vtype}::{vid}"
                    temporal_counts[tkey] += 1
                    if tkey not in temporal_best or conf > temporal_best[tkey].get("confidence", 0):
                        temporal_best[tkey] = v
                    if tkey not in confirmed_keys:
                        if temporal_counts[tkey] >= 2 or conf >= 0.38:
                            c = _clean_viols([v])[0]
                            c["sightings"] = temporal_counts[tkey]
                            try:
                                ev, db_id = _persist_violation(c, processed, camera_id)
                                c["evidence_hash"] = ev
                                c["db_id"] = db_id
                            except Exception:
                                pass
                            confirmed_viols.append(c)
                            confirmed_keys.add(tkey)
                            new_confirmed.append(c)

                annotated = annotate(processed, viols, vehicles=vehicles)
                if stopline_enabled:
                    cv2.line(annotated, (0, stop_line_y), (annotated.shape[1], stop_line_y), (0,0,255), 2)
                h, w = annotated.shape[:2]
                if w > 960:
                    annotated = cv2.resize(annotated, (960, int(h * 960 / w)))
                _, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 72])
                frame_b64 = base64.b64encode(buf).decode()

                payload = json.dumps({
                    "frame":           frame_count,
                    "total":           max_frames,
                    "progress":        round(frame_count / max(max_frames, 1) * 100),
                    "frame_b64":       frame_b64,
                    "current_viols":   _clean_viols(viols),
                    "confirmed_viols": confirmed_viols,
                    "new_confirmed":   new_confirmed,
                    "done":            False,
                })
                yield f"data: {payload}\n\n"
                await asyncio.sleep(0)

        finally:
            if cap:
                cap.release()
            if ff_proc:
                ff_proc.terminate()
                try:
                    ff_proc.wait(timeout=3)
                except Exception:
                    pass

        yield f"data: {json.dumps({'done': True, 'violations': confirmed_viols, 'total_frames': frame_count, 'frames_analysed': analysed_count})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no",
                 "Connection": "keep-alive", "Access-Control-Allow-Origin": "*"})


# ── Plate clone check ─────────────────────────────────────────────────────────
@app.get("/api/graph/clone/{plate}", dependencies=[Depends(require_auth)])
def clone_check(plate: str, window_minutes: int = 30):
    cutoff = (datetime.now() - timedelta(minutes=window_minutes)).timestamp()
    con = _db(); cur = con.cursor()
    cur.execute("""
        SELECT camera_id, timestamp, violation_type FROM violations
        WHERE UPPER(plate_number)=? AND timestamp>? ORDER BY timestamp DESC
    """, (plate.upper(), cutoff))
    rows = [dict(r) for r in cur.fetchall()]
    con.close()
    locations = list({r["camera_id"] for r in rows})
    return {"plate": plate.upper(), "sightings": rows,
            "unique_locations": locations, "clone_alert": len(locations) > 1}

# ── Evidence verify ───────────────────────────────────────────────────────────
class VerifyBody(BaseModel):
    evidence_hash: str

@app.post("/api/verify", dependencies=[Depends(require_auth)])
def verify_evidence(body: VerifyBody):
    con = _db(); cur = con.cursor()
    cur.execute("SELECT * FROM violations WHERE evidence_hash=?", (body.evidence_hash,))
    row = cur.fetchone()
    con.close()
    if not row:
        return {"found": False, "message": "No record found for this hash"}
    d = _row_to_dict(row)
    snap_full = SNAP_DIR / f"{body.evidence_hash[:16]}_full.jpg"
    snap_crop = SNAP_DIR / f"{body.evidence_hash[:16]}_crop.jpg"
    return {"found": True, "record": d,
            "snapshots": {"full": snap_full.exists(), "crop": snap_crop.exists()}}

# ── Snapshot image ────────────────────────────────────────────────────────────
@app.get("/api/snapshot/{hash16}/{kind}", dependencies=[Depends(require_auth)])
def snapshot(hash16: str, kind: str):
    if kind not in ("full", "crop"):
        raise HTTPException(400, "kind must be 'full' or 'crop'")
    path = SNAP_DIR / f"{hash16}_{kind}.jpg"
    if not path.exists():
        raise HTTPException(404, "Snapshot not found")
    return FileResponse(str(path), media_type="image/jpeg")

# ── Video upload + SSE streaming ──────────────────────────────────────────────
@app.post("/api/detect/video/upload", dependencies=[Depends(require_auth)])
async def upload_video_for_stream(request: Request, file: UploadFile = File(...)):
    _check_rate(request, max_per_minute=5)
    data = await file.read()
    if len(data) > MAX_VIDEO_BYTES:
        raise HTTPException(413, f"Video exceeds {MAX_VIDEO_BYTES // 1024 // 1024}MB limit")

    suffix = Path(file.filename or "vid.mp4").suffix or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    sid = str(uuid.uuid4())
    _video_sessions[sid] = (tmp_path, time.time())
    return {"session_id": sid}


@app.get("/api/detect/video/stream/{sid}", dependencies=[Depends(require_auth)])
async def stream_video_analysis(
    sid: str,
    stop_line_y: int = 400,
    frame_skip:  int = 6,
    max_seconds: int = 60,
    signal_red:         bool = False,
    stopline_enabled:   bool = False,
    scene_type:         str  = "Junction",
    wrong_side_present: bool = False,
    flow_direction:     str  = "Left -> Right",
    camera_id:          str  = "live_upload",
):
    tmp_path = _get_session_path(sid)

    reset_tracking(); reset_id_map()
    yolo = _yolo()

    async def generate():
        cap        = cv2.VideoCapture(tmp_path)
        fps        = cap.get(cv2.CAP_PROP_FPS) or 25.0
        max_frames = int(max_seconds * fps)
        frame_count    = 0
        analysed_count = 0
        temporal_counts: dict = defaultdict(int)
        temporal_best:   dict = {}
        confirmed_viols: list = []
        confirmed_types: set  = set()

        try:
            while True:
                ok, raw_frame = cap.read()
                if not ok or frame_count >= max_frames:
                    break
                frame_count += 1
                if frame_count % frame_skip != 0:
                    continue

                h0, w0 = raw_frame.shape[:2]
                scale_down = min(1.0, 640 / max(w0, 1))
                if scale_down < 1.0:
                    small = cv2.resize(raw_frame, (int(w0 * scale_down), int(h0 * scale_down)))
                else:
                    small = raw_frame

                processed  = preprocess(small, True)
                analysed_count += 1

                res = yolo.track(processed, persist=True, verbose=False)

                det_result = detect_violations(
                    res, int(stop_line_y * scale_down), processed.shape[:2],
                    frame_bgr=processed,
                    helmet_model=_helmet(),
                    seatbelt_model=_seatbelt(),
                    wrongside_model=_wrongside(),
                    signal_red=signal_red,
                    stopline_enabled=stopline_enabled,
                    scene_type=scene_type,
                    wrong_side_present=wrong_side_present,
                    flow_direction=flow_direction,
                )
                viols    = det_result["violations"]
                vehicles = det_result["vehicles"]
                _add_vehicle_category(viols, processed)

                new_confirmed = []
                for v in viols:
                    v["frame"] = frame_count
                    vtype = v.get("type", "")
                    vid   = v.get("vehicle_id", "unknown")
                    conf  = v.get("confidence", 0)
                    tkey  = f"{vtype}::{vid}"

                    temporal_counts[tkey] += 1
                    if tkey not in temporal_best or conf > temporal_best[tkey].get("confidence", 0):
                        temporal_best[tkey] = v

                    if tkey not in confirmed_types:
                        if temporal_counts[tkey] >= 2 or conf >= 0.38:
                            c = _clean_viols([v])[0]
                            c["sightings"] = temporal_counts[tkey]
                            try:
                                ev, db_id = _persist_violation(c, processed, camera_id)
                                c["evidence_hash"] = ev
                                c["db_id"] = db_id
                            except Exception:
                                pass
                            confirmed_viols.append(c)
                            confirmed_types.add(tkey)
                            new_confirmed.append(c)

                annotated = annotate(processed, viols, vehicles=vehicles)
                if stopline_enabled:
                    cv2.line(annotated, (0, stop_line_y), (annotated.shape[1], stop_line_y), (0, 0, 255), 2)
                    cv2.putText(annotated, "STOP LINE", (8, stop_line_y - 6),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)

                h, w = annotated.shape[:2]
                if w > 960:
                    scale     = 960 / w
                    annotated = cv2.resize(annotated, (960, int(h * scale)))

                _, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 72])
                frame_b64 = base64.b64encode(buf).decode()

                payload = json.dumps({
                    "frame":           frame_count,
                    "total":           max_frames,
                    "progress":        round(frame_count / max(max_frames, 1) * 100),
                    "frame_b64":       frame_b64,
                    "current_viols":   _clean_viols(viols),
                    "confirmed_viols": confirmed_viols,
                    "new_confirmed":   new_confirmed,
                    "done":            False,
                })
                yield f"data: {payload}\n\n"
                await asyncio.sleep(0)

        finally:
            cap.release()
            entry = _video_sessions.pop(sid, None)
            if entry:
                try:
                    Path(entry[0]).unlink(missing_ok=True)
                except Exception:
                    pass

        yield f"data: {json.dumps({'done': True, 'violations': confirmed_viols, 'total_frames': frame_count, 'frames_analysed': frame_count // max(frame_skip, 1)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":      "no-cache",
            "X-Accel-Buffering":  "no",
            "Connection":         "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )


# ── AI Agent (Ollama-powered with rule-based fallback) ────────────────────────
def _build_db_context() -> str:
    con = _db(); cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM violations"); total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM violations WHERE operator_action IS NULL"); pending = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM violations WHERE priority_level='CRITICAL'"); critical = cur.fetchone()[0]
    cur.execute("SELECT violation_type, COUNT(*) as c FROM violations GROUP BY violation_type ORDER BY c DESC LIMIT 6")
    top_types = "; ".join(f"{r[0]}({r[1]})" for r in cur.fetchall())
    cur.execute("SELECT camera_id, COUNT(*) as c FROM violations GROUP BY camera_id ORDER BY c DESC LIMIT 4")
    top_cams  = "; ".join(f"{r[0]}({r[1]})" for r in cur.fetchall())
    cur.execute("SELECT plate_number, COUNT(*) as c FROM violations WHERE plate_number!='UNREADABLE' GROUP BY plate_number HAVING c>=2 ORDER BY c DESC LIMIT 5")
    offenders = "; ".join(f"{r[0]}({r[1]} times)" for r in cur.fetchall())
    since_24h = (datetime.now() - timedelta(hours=24)).timestamp()
    cur.execute("SELECT COUNT(*) FROM violations WHERE timestamp>?", (since_24h,)); today = cur.fetchone()[0]
    con.close()
    return (
        f"DrishtiVia traffic violation database summary:\n"
        f"- Total violations: {total}\n"
        f"- Pending review: {pending}\n"
        f"- CRITICAL violations: {critical}\n"
        f"- Last 24 hours: {today}\n"
        f"- Top violation types: {top_types}\n"
        f"- Top cameras by violations: {top_cams}\n"
        f"- Repeat offenders (>=2): {offenders or 'none'}\n"
        f"- Models: Wrong-Side (mAP50=0.977, P=0.943, R=0.961), Seatbelt (mAP50=0.911, P=0.912, R=0.842), "
        f"Helmet (mAP50=0.788, P=0.845, R=0.626), + base YOLOv8s for Triple Riding / Stop-Line / Parking\n"
        f"- Preprocessing: CLAHE + dark-channel dehazing active on every frame\n"
        f"- Confirmation: temporal 2-sighting confirmation before alerting\n"
    )


def _try_ollama(question: str, context: str) -> str | None:
    try:
        tags_r = http_requests.get("http://localhost:11434/api/tags", timeout=3)
        if tags_r.status_code != 200:
            return None
        models = [m["name"] for m in tags_r.json().get("models", [])]
        if not models:
            return None
        # Prefer small fast models — 1b/3b respond in ~5s on CPU vs 30s for 7b
        preferred = (
            next((m for m in models if "llama3.2:1b" in m.lower()), None) or
            next((m for m in models if "llama3.2:3b" in m.lower()), None) or
            next((m for m in models if "llama3" in m.lower()), None) or
            next((m for m in models if "phi3" in m.lower()), None) or
            next((m for m in models if "mistral" in m.lower()), None) or
            models[0]
        )
    except Exception:
        return None

    # Estimate timeout: 1b/3b models are fast; 7b+ need longer on CPU
    is_large = any(tag in preferred for tag in ["7b", "8b", "13b", "70b"])
    timeout_s = 50 if is_large else 20

    try:
        r = http_requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model":  preferred,
                "system": (
                    "You are DrishtiVia AI Agent — an assistant for a Bengaluru traffic "
                    "violation detection system. Answer concisely using the database context provided. "
                    "Use markdown bold (**text**) for emphasis. Keep answers under 80 words."
                ),
                "prompt": f"Database context:\n{context}\n\nQuestion: {question}",
                "stream": False,
                "options": {
                    "num_predict": 120,
                    "temperature": 0.3,
                    "num_gpu": 0,      # force CPU — avoids CUDA_Host OOM on large models
                },
            },
            timeout=timeout_s,
        )
        if r.status_code == 200:
            ans = r.json().get("response", "").strip()
            if ans:
                return ans
    except Exception:
        pass
    return None


class AgentQuery(BaseModel):
    question: str

@app.post("/api/agent", dependencies=[Depends(require_auth)])
def agent_query(body: AgentQuery):
    q       = body.question.strip()
    context = _build_db_context()

    ollama_answer = _try_ollama(q, context)
    if ollama_answer:
        return {"answer": ollama_answer, "question": body.question, "source": "ollama"}

    ql  = q.lower()
    con = _db(); cur = con.cursor()
    answer = None

    if any(w in ql for w in ["how many violation", "total violation", "count"]):
        cur.execute("SELECT COUNT(*) FROM violations")
        n = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM violations WHERE operator_action IS NULL")
        p = cur.fetchone()[0]
        answer = f"There are **{n} total violations** in the database. **{p}** are still pending review."

    elif any(w in ql for w in ["most common", "top violation", "frequent"]):
        cur.execute("SELECT violation_type, COUNT(*) as c FROM violations GROUP BY violation_type ORDER BY c DESC LIMIT 3")
        rows = cur.fetchall()
        lines = [f"{i+1}. **{r[0]}** — {r[1]} incidents" for i, r in enumerate(rows)]
        answer = "Top 3 violation types:\n" + "\n".join(lines)

    elif any(w in q for w in ["worst camera", "hotspot", "most violation camera", "busiest"]):
        cur.execute("SELECT camera_id, COUNT(*) as c FROM violations GROUP BY camera_id ORDER BY c DESC LIMIT 1")
        r = cur.fetchone()
        answer = f"The camera with the most violations is **{r[0]}** with **{r[1]} recorded incidents**." if r else "No camera data found yet."

    elif any(w in q for w in ["repeat offend", "serial", "multiple violation"]):
        cur.execute("""
            SELECT plate_number, COUNT(*) as c,
                   GROUP_CONCAT(DISTINCT violation_type) as types
            FROM violations WHERE plate_number != 'UNREADABLE'
            GROUP BY plate_number HAVING c >= 2 ORDER BY c DESC LIMIT 5
        """)
        rows = cur.fetchall()
        if rows:
            lines = [f"- **{r[0]}** — {r[1]} violations ({r[2]})" for r in rows]
            answer = "Repeat offenders (≥2 violations):\n" + "\n".join(lines)
        else:
            answer = "No repeat offenders found in the database yet."

    elif any(w in q for w in ["pending", "unreviewed", "need review", "action"]):
        cur.execute("SELECT COUNT(*) FROM violations WHERE operator_action IS NULL")
        n = cur.fetchone()[0]
        cur.execute("""
            SELECT violation_type, COUNT(*) as c
            FROM violations WHERE operator_action IS NULL
            GROUP BY violation_type ORDER BY c DESC LIMIT 3
        """)
        rows = cur.fetchall()
        lines = [f"- {r[0]}: {r[1]}" for r in rows]
        answer = f"**{n} violations** are pending review. Top pending types:\n" + "\n".join(lines)

    elif re.search(r"[A-Z]{2}\d{2}", q.upper()):
        plate_match = re.search(r"[A-Z]{2}\d{2}[A-Z0-9]+", q.upper())
        if plate_match:
            plate = plate_match.group()
            cur.execute("SELECT * FROM violations WHERE UPPER(plate_number) LIKE ? ORDER BY timestamp DESC LIMIT 5", (f"%{plate}%",))
            rows = cur.fetchall()
            if rows:
                lines = [f"- {dict(r)['violation_type']} ({dict(r)['priority_level']}) at {dict(r)['camera_id']} — {datetime.fromtimestamp(dict(r)['timestamp']).strftime('%Y-%m-%d %H:%M')}" for r in rows]
                answer = f"Found **{len(rows)} record(s)** for plate `{plate}`:\n" + "\n".join(lines)
            else:
                answer = f"No records found for plate `{plate}`."

    elif any(w in q for w in ["critical", "severe", "dangerous", "urgent"]):
        cur.execute("SELECT COUNT(*) FROM violations WHERE priority_level='CRITICAL'")
        n = cur.fetchone()[0]
        cur.execute("""
            SELECT violation_type, camera_id, plate_number
            FROM violations WHERE priority_level='CRITICAL'
            ORDER BY timestamp DESC LIMIT 3
        """)
        rows = cur.fetchall()
        lines = [f"- {r[0]} | {r[1]} | plate: {r[2]}" for r in rows]
        answer = f"**{n} CRITICAL violations** on record. Most recent:\n" + "\n".join(lines)

    elif any(w in q for w in ["today", "this morning", "last hour"]):
        since = (datetime.now() - timedelta(hours=24)).timestamp()
        cur.execute("SELECT COUNT(*) FROM violations WHERE timestamp > ?", (since,))
        n = cur.fetchone()[0]
        answer = f"**{n} violations** recorded in the last 24 hours."

    elif "helmet" in q:
        cur.execute("SELECT COUNT(*) FROM violations WHERE violation_type='Helmet Non-Compliance'")
        n = cur.fetchone()[0]
        answer = f"**{n} Helmet Non-Compliance** violations on record. The model uses a fine-tuned YOLOv8 classifier at 0.45 confidence threshold for HIGH severity, 0.20 for MEDIUM (human review required)."

    elif any(w in q for w in ["wrong side", "wrong-side", "opposite"]):
        cur.execute("SELECT COUNT(*) FROM violations WHERE violation_type='Wrong-Side Driving'")
        n = cur.fetchone()[0]
        answer = f"**{n} Wrong-Side Driving** violations on record. This uses a fine-tuned model with mAP50=0.977 — your highest-accuracy detector."

    elif "seatbelt" in q or "seat belt" in q:
        cur.execute("SELECT COUNT(*) FROM violations WHERE violation_type='Seatbelt Non-Compliance'")
        n = cur.fetchone()[0]
        answer = f"**{n} Seatbelt Non-Compliance** violations. The model achieved mAP50=0.911 (precision 0.912, recall 0.842)."

    elif any(w in q for w in ["accuracy", "model", "map", "precision", "recall"]):
        answer = (
            "**Model accuracy summary:**\n"
            "- Wrong-Side Driving: mAP50 **0.977**, P=0.943, R=0.961 (fine-tuned YOLOv8)\n"
            "- Seatbelt: mAP50 **0.911**, P=0.912, R=0.842 (fine-tuned)\n"
            "- Helmet: mAP50 **0.788**, P=0.845, R=0.626 (fine-tuned, threshold 0.55 HIGH / 0.35 MEDIUM)\n"
            "- Triple Riding: Geometric overlap + posture filter (base COCO model)\n"
            "- Illegal Parking: ByteTrack position history (< 20px / 90 frames)\n"
            "- Stop-Line/Red-Light: Y-threshold crossing (base COCO bbox)"
        )

    else:
        cur.execute("SELECT COUNT(*) FROM violations")
        total = cur.fetchone()[0]
        cur.execute("SELECT violation_type, COUNT(*) as c FROM violations GROUP BY violation_type ORDER BY c DESC LIMIT 1")
        top = cur.fetchone()
        answer = (
            f"I can answer questions about the **{total} violations** in your database. "
            f"Most common: **{top[0] if top else 'N/A'}**. "
            "Try asking: 'How many violations today?', 'Who are the repeat offenders?', "
            "'What is the most common violation?', 'Show me CRITICAL violations'."
        )

    con.close()
    return {"answer": answer, "question": body.question}


@app.get("/api/agent/stream", dependencies=[Depends(require_auth)])
async def agent_stream(question: str):
    """SSE endpoint — streams Ollama tokens in real time, falls back to rule-based."""
    q       = question.strip()
    context = _build_db_context()

    async def generate():
        # Check if Ollama is available
        try:
            tags_r = http_requests.get("http://localhost:11434/api/tags", timeout=3)
            models = [m["name"] for m in tags_r.json().get("models", [])] if tags_r.status_code == 200 else []
        except Exception:
            models = []

        if models:
            preferred = (
                next((m for m in models if "llama3.2:1b" in m.lower()), None) or
                next((m for m in models if "llama3.2" in m.lower()), None) or
                next((m for m in models if "llama3" in m.lower()), None) or
                next((m for m in models if "phi3" in m.lower()), None) or
                next((m for m in models if "mistral" in m.lower()), None) or
                models[0]
            )
            yield f"data: {json.dumps({'token': '', 'source': 'ollama', 'model': preferred})}\n\n"
            await asyncio.sleep(0)

            try:
                # Use requests with stream=True so we get tokens as they arrive
                def _stream_ollama():
                    return http_requests.post(
                        "http://localhost:11434/api/generate",
                        json={
                            "model": preferred,
                            "system": (
                                "You are DrishtiVia AI Agent for a Bengaluru traffic violation system. "
                                "Answer concisely using the data provided. Use **bold** for emphasis. "
                                "Keep answers under 80 words."
                            ),
                            "prompt": f"Database context:\n{context}\n\nQuestion: {q}",
                            "stream": True,
                            "options": {"num_predict": 120, "temperature": 0.3, "num_gpu": 0},
                        },
                        stream=True,
                        timeout=60,
                    )

                resp = await asyncio.get_event_loop().run_in_executor(None, _stream_ollama)
                if resp.status_code == 200:
                    for line in resp.iter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                            token = chunk.get("response", "")
                            if token:
                                yield f"data: {json.dumps({'token': token})}\n\n"
                                await asyncio.sleep(0)
                            if chunk.get("done"):
                                yield f"data: {json.dumps({'done': True, 'source': 'ollama'})}\n\n"
                                return
                        except Exception:
                            continue
                    yield f"data: {json.dumps({'done': True, 'source': 'ollama'})}\n\n"
                    return
            except Exception:
                pass  # fall through to rule-based

        # Rule-based fallback — emit answer as single token burst
        body_obj = AgentQuery(question=q)
        result   = agent_query(body_obj)
        answer   = result.get("answer", "")
        yield f"data: {json.dumps({'token': answer, 'source': 'rule-based'})}\n\n"
        yield f"data: {json.dumps({'done': True, 'source': 'rule-based'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no",
                 "Connection": "keep-alive", "Access-Control-Allow-Origin": "*"})


# ── Escalation report ─────────────────────────────────────────────────────────
@app.get("/api/report/{vid}", dependencies=[Depends(require_auth)])
def generate_report(vid: int):
    con = _db(); cur = con.cursor()
    cur.execute("SELECT * FROM violations WHERE id=?", (vid,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Violation not found")
    d = _row_to_dict(row)
    con.close()

    ts = datetime.fromtimestamp(d.get("timestamp", 0)).strftime("%Y-%m-%d %H:%M:%S")
    report_id = f"VV-{vid:06d}-{datetime.now().strftime('%Y%m%d')}"
    html = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<title>DrishtiVia Escalation Report {report_id}</title>
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #111; }}
  h1 {{ font-size: 22px; font-weight: 700; margin-bottom: 4px; }}
  .badge {{ display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight: 700;
            background: {"#fee2e2" if d.get("priority_level")=="CRITICAL" else "#ffedd5" if d.get("priority_level")=="HIGH" else "#fefce8"};
            color: {"#991b1b" if d.get("priority_level")=="CRITICAL" else "#9a3412" if d.get("priority_level")=="HIGH" else "#713f12"}; }}
  table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid #f0f0f0; font-size: 14px; }}
  td:first-child {{ font-weight: 600; color: #555; width: 200px; }}
  .section {{ font-size: 11px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: #aaa; margin: 24px 0 8px; }}
  .footer {{ font-size: 11px; color: #aaa; border-top: 1px solid #eee; padding-top: 16px; margin-top: 32px; }}
  .stamp {{ background: #111; color: #fff; padding: 8px 18px; border-radius: 8px; display: inline-block; font-size: 13px; font-weight: 600; margin-top: 8px; }}
  @media print {{ body {{ margin: 20px; }} }}
</style>
</head><body>
<p style="font-size:11px;color:#999;margin-bottom:4px">DrishtiVia 2.0 · BENGALURU TRAFFIC CONTROL ROOM · CONFIDENTIAL</p>
<h1>Escalation Report</h1>
<p style="margin:0;font-size:14px;color:#555">Report ID: <strong>{report_id}</strong> &nbsp;·&nbsp; Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
<p style="margin-top:8px"><span class="badge">{d.get("priority_level","LOW")}</span></p>

<p class="section">Violation Details</p>
<table>
  <tr><td>Violation Type</td><td><strong>{d.get("violation_type","—")}</strong></td></tr>
  <tr><td>Date & Time</td><td>{ts}</td></tr>
  <tr><td>Camera Location</td><td>{d.get("camera_id","—")}</td></tr>
  <tr><td>Plate Number</td><td><strong>{d.get("plate_number","UNREADABLE")}</strong></td></tr>
  <tr><td>Confidence Score</td><td>{round((d.get("confidence",0))*100,1)}%</td></tr>
  <tr><td>Priority Score</td><td>{d.get("priority_score","—")}</td></tr>
  <tr><td>Priority Level</td><td>{d.get("priority_level","—")}</td></tr>
</table>

<p class="section">Evidence Chain of Custody</p>
<table>
  <tr><td>Evidence Hash</td><td style="font-family:monospace;font-size:12px">{d.get("evidence_hash","—")}</td></tr>
  <tr><td>Hash Algorithm</td><td>SHA-256</td></tr>
  <tr><td>Signing Method</td><td>RSA-PSS (software key — prototype)</td></tr>
  <tr><td>Operator Action</td><td>{d.get("operator_action","PENDING") or "PENDING"}</td></tr>
</table>

<p class="section">Escalation Reason</p>
<p style="font-size:14px;color:#333">This violation has been flagged for escalation due to its <strong>{d.get("priority_level","HIGH")} severity</strong>.
Immediate enforcement action is recommended. Please verify the plate number against the VAHAN database and initiate challan proceedings.</p>

<p class="section">Recommended Action</p>
<table>
  <tr><td>Immediate</td><td>Issue e-challan via VAHAN portal for plate {d.get("plate_number","—")}</td></tr>
  <tr><td>Evidence</td><td>Snapshot stored in evidence_store/snapshots/ — attach to challan</td></tr>
  <tr><td>Follow-up</td><td>Check repeat-offender status in Knowledge Graph</td></tr>
</table>

<div class="footer">
  <p>This report was auto-generated by DrishtiVia 2.0 · Flipkart Gridlock Hackathon 2.0 · Prototype system · Not for production enforcement without human review.</p>
  <div class="stamp">DrishtiVia 2.0 — Authorised System Output</div>
</div>
<script>window.onload = function(){{ window.print(); }}</script>
</body></html>"""
    return HTMLResponse(content=html)
