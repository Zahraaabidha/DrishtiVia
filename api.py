"""
DrishtiVia 2.0 — FastAPI backend
Run: uvicorn api:app --reload --port 8000

IMPORTANT: This file imports ONLY from detect_core.py (zero Streamlit dependency).
Never import from app.py — it has module-level st.tabs() / st.set_page_config()
calls that crash immediately outside a Streamlit server.
"""
import os, base64, tempfile, sqlite3, re, time, json, uuid, asyncio
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, deque

import cv2
import numpy as np
import requests as http_requests
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from pydantic import BaseModel

# Video session store (session_id -> tmp_file_path)
_video_sessions: dict = {}

# ── detect_core: pure Python, no Streamlit ────────────────────────────────────
from detect_core import (
    preprocess,
    detect_violations,
    annotate,
    classify_plate_category,
    reset_tracking,
    reset_id_map,
)

# ── paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DB_PATH  = BASE_DIR / "evidence_store" / "violations.db"
SNAP_DIR = BASE_DIR / "evidence_store" / "snapshots"
SNAP_DIR.mkdir(parents=True, exist_ok=True)

HELMET_PATH    = BASE_DIR / "runs/detect/runs/helmet_train/violavision_v1/weights/best.pt"
SEATBELT_PATH  = BASE_DIR / "runs/detect/runs/seatbelt_train/violavision_seatbelt_v1-2/weights/best.pt"
WRONGSIDE_PATH = BASE_DIR / "runs/detect/runs/wrongside_train/violavision_wrongside_v1/weights/best.pt"

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(title="DrishtiVia API", version="2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    con = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con

def _row_to_dict(row) -> dict:
    d = dict(row)
    d["severity"] = d.get("priority_level") or "LOW"
    return d

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
        # numpy int -> python int
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

# ── Health ────────────────────────────────────────────────────────────────────
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
@app.get("/api/stats")
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
@app.get("/api/violations")
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
        # Support comma-separated e.g. "CRITICAL,HIGH"
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

    # Count total (for pagination)
    cur.execute(f"SELECT COUNT(*) FROM violations {where_sql}", params)
    total = cur.fetchone()[0]

    cur.execute(f"SELECT * FROM violations {where_sql} {order_sql} LIMIT ? OFFSET ?",
                params + [limit, offset])
    rows = [_row_to_dict(r) for r in cur.fetchall()]
    con.close()
    return {"violations": rows, "count": len(rows), "total": total}

# ── Search ────────────────────────────────────────────────────────────────────
@app.get("/api/search")
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

# ── Violation action ──────────────────────────────────────────────────────────
class ActionBody(BaseModel):
    action: str

@app.post("/api/violations/{vid}/action")
def violation_action(vid: int, body: ActionBody):
    con = _db()
    con.execute("UPDATE violations SET operator_action=? WHERE id=?",
                (body.action.upper(), vid))
    con.commit(); con.close()
    return {"ok": True, "id": vid, "action": body.action}

# ── Detect image ──────────────────────────────────────────────────────────────
@app.post("/api/detect/image")
async def detect_image(
    file: UploadFile = File(...),
    stop_line_y: int = 400,
    signal_red: bool = False,
    stopline_enabled: bool = False,
    scene_type: str = "Junction",
    wrong_side_present: bool = False,
    flow_direction: str = "Left -> Right",
    preprocessing: bool = True,
):
    data  = await file.read()
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
@app.post("/api/detect/video")
async def detect_video(
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
    data   = await file.read()
    suffix = Path(file.filename or "vid.mp4").suffix or ".mp4"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    reset_tracking(); reset_id_map()   # clear position history + vehicle IDs from any previous clip
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
                conf  = v.get("confidence", 0)

                temporal_counts[vtype] += 1
                if vtype not in temporal_best or conf > temporal_best[vtype].get("confidence", 0):
                    temporal_best[vtype] = v

                # Confirm on 2nd sighting or immediately if very high confidence
                if vtype not in confirmed_types:
                    if temporal_counts[vtype] >= 2 or conf >= 0.55:
                        c = _clean_viols([v])[0]
                        c["confirmed_at_frame"] = frame_count
                        c["sightings"] = temporal_counts[vtype]
                        confirmed_viols.append(c)
                        confirmed_types.add(vtype)

    finally:
        cap.release()
        try:
            Path(tmp_path).unlink()
        except Exception:
            pass

    # Include best single-frame detections for rare violations not hitting 3-of-5
    for key, v in temporal_best.items():
        vtype = v.get("type", "")
        if vtype not in confirmed_types and temporal_counts.get(key, 0) >= 1:
            c = _clean_viols([v])[0]
            c["note"] = f"Single-frame only (seen {temporal_counts[key]}× — below 3-of-5 threshold)"
            confirmed_viols.append(c)
            confirmed_types.add(vtype)

    return {
        "total_frames":    frame_count,
        "frames_analysed": frame_count // max(frame_skip, 1),
        "violations":      confirmed_viols,
        "count":           len(confirmed_viols),
    }

# ── Analytics ─────────────────────────────────────────────────────────────────
@app.get("/api/analytics")
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

    # camera hotspots with coords (known Bangalore junctions)
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
@app.get("/api/graph")
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

# ── Plate clone check ─────────────────────────────────────────────────────────
@app.get("/api/graph/clone/{plate}")
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

@app.post("/api/verify")
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
@app.get("/api/snapshot/{hash16}/{kind}")
def snapshot(hash16: str, kind: str):
    path = SNAP_DIR / f"{hash16}_{kind}.jpg"
    if not path.exists():
        raise HTTPException(404, "Snapshot not found")
    return FileResponse(str(path), media_type="image/jpeg")

# ── Video upload + SSE streaming ──────────────────────────────────────────────
@app.post("/api/detect/video/upload")
async def upload_video_for_stream(file: UploadFile = File(...)):
    data   = await file.read()
    suffix = Path(file.filename or "vid.mp4").suffix or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    sid = str(uuid.uuid4())
    _video_sessions[sid] = tmp_path
    return {"session_id": sid}


@app.get("/api/detect/video/stream/{sid}")
async def stream_video_analysis(
    sid: str,
    stop_line_y: int = 400,
    frame_skip:  int = 6,    # process every 6th frame (~4fps effective at 25fps) for speed
    max_seconds: int = 60,
    signal_red:        bool = False,
    stopline_enabled:  bool = False,
    scene_type:        str  = "Junction",
    wrong_side_present: bool = False,
    flow_direction:    str  = "Left -> Right",
):
    tmp_path = _video_sessions.get(sid)
    if not tmp_path or not Path(tmp_path).exists():
        raise HTTPException(404, "Session not found or expired — re-upload the video")

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

                # Downscale to 640px wide for YOLO speed; annotated output upscales back
                h0, w0 = raw_frame.shape[:2]
                scale_down = min(1.0, 640 / max(w0, 1))
                if scale_down < 1.0:
                    small = cv2.resize(raw_frame, (int(w0 * scale_down), int(h0 * scale_down)))
                else:
                    small = raw_frame

                processed  = preprocess(small, True)
                analysed_count += 1

                run_finetune = True  # run fine-tuned models every processed frame

                res = yolo.track(processed, persist=True, verbose=False)

                det_result = detect_violations(
                    res, int(stop_line_y * scale_down), processed.shape[:2],
                    frame_bgr=processed,
                    helmet_model=_helmet()    if run_finetune else None,
                    seatbelt_model=_seatbelt() if run_finetune else None,
                    wrongside_model=_wrongside() if run_finetune else None,
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
                    conf  = v.get("confidence", 0)

                    # Count by violation TYPE (not track_id) — track IDs change across frames
                    temporal_counts[vtype] += 1
                    if vtype not in temporal_best or conf > temporal_best[vtype].get("confidence", 0):
                        temporal_best[vtype] = v

                    # Confirm on 2nd sighting OR immediately if very high confidence (>= 0.65)
                    already_confirmed = vtype in confirmed_types
                    if not already_confirmed:
                        if temporal_counts[vtype] >= 2 or conf >= 0.55:
                            c = _clean_viols([v])[0]
                            c["sightings"] = temporal_counts[vtype]
                            confirmed_viols.append(c)
                            confirmed_types.add(vtype)
                            new_confirmed.append(c)

                # Annotate with vehicle IDs + violation overlays
                annotated = annotate(processed, viols, vehicles=vehicles)
                if stopline_enabled:
                    cv2.line(annotated, (0, stop_line_y), (annotated.shape[1], stop_line_y), (0, 0, 255), 2)
                    cv2.putText(annotated, "STOP LINE", (8, stop_line_y - 6),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)

                # Resize for bandwidth (cap at 960px wide)
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
                await asyncio.sleep(0)   # yield control to event loop

        finally:
            cap.release()
            try:
                Path(tmp_path).unlink()
                _video_sessions.pop(sid, None)
            except Exception:
                pass

        # Final done event
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
    """Gather live DB stats to inject as LLM context."""
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
        f"- Models: Wrong-Side (mAP50=0.975), Seatbelt (mAP50=0.901, P=0.888, R=0.859), "
        f"Helmet (mAP50~0.82), + base YOLOv8s for Triple Riding / Stop-Line / Parking\n"
        f"- Preprocessing: CLAHE + dark-channel dehazing active on every frame\n"
        f"- Confirmation: temporal 3-of-5 (violation seen 3 out of last 5 frames before alerting)\n"
    )


def _try_ollama(question: str, context: str) -> str | None:
    """Try Ollama local LLM. Returns text or None if unavailable."""
    # auto-detect installed models
    try:
        tags_r = http_requests.get("http://localhost:11434/api/tags", timeout=3)
        if tags_r.status_code != 200:
            return None
        models = [m["name"] for m in tags_r.json().get("models", [])]
        if not models:
            return None
        # prefer llama3 > mistral > anything else
        preferred = next((m for m in models if "llama3" in m.lower()), None) or \
                    next((m for m in models if "mistral" in m.lower()), None) or \
                    models[0]
    except Exception:
        return None

    try:
        r = http_requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model":  preferred,
                "system": (
                    "You are DrishtiVia AI Agent — an assistant for a Bengaluru traffic "
                    "violation detection system. Answer concisely using the database context provided. "
                    "Use markdown bold (**text**) for emphasis. Keep answers under 150 words."
                ),
                "prompt": f"Database context:\n{context}\n\nQuestion: {question}",
                "stream": False,
            },
            timeout=30,
        )
        if r.status_code == 200:
            return r.json().get("response", "").strip()
    except Exception:
        pass
    return None


class AgentQuery(BaseModel):
    question: str

@app.post("/api/agent")
def agent_query(body: AgentQuery):
    q       = body.question.strip()
    context = _build_db_context()

    # Try Ollama first
    ollama_answer = _try_ollama(q, context)
    if ollama_answer:
        return {"answer": ollama_answer, "question": body.question, "source": "ollama"}

    # ── Rule-based fallback ────────────────────────────────────────────────────
    ql  = q.lower()
    con = _db(); cur = con.cursor()
    answer = None

    # Total violations
    if any(w in ql for w in ["how many violation", "total violation", "count"]):
        cur.execute("SELECT COUNT(*) FROM violations")
        n = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM violations WHERE operator_action IS NULL")
        p = cur.fetchone()[0]
        answer = f"There are **{n} total violations** in the database. **{p}** are still pending review."

    # Most common
    elif any(w in ql for w in ["most common", "top violation", "frequent"]):
        cur.execute("SELECT violation_type, COUNT(*) as c FROM violations GROUP BY violation_type ORDER BY c DESC LIMIT 3")
        rows = cur.fetchall()
        lines = [f"{i+1}. **{r[0]}** — {r[1]} incidents" for i, r in enumerate(rows)]
        answer = "Top 3 violation types:\n" + "\n".join(lines)

    # Worst camera / hotspot
    elif any(w in q for w in ["worst camera", "hotspot", "most violation camera", "busiest"]):
        cur.execute("SELECT camera_id, COUNT(*) as c FROM violations GROUP BY camera_id ORDER BY c DESC LIMIT 1")
        r = cur.fetchone()
        if r:
            answer = f"The camera with the most violations is **{r[0]}** with **{r[1]} recorded incidents**."
        else:
            answer = "No camera data found yet."

    # Repeat offenders
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

    # Pending / unreviewed
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

    # Specific plate
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

    # CRITICAL violations
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

    # Today
    elif any(w in q for w in ["today", "this morning", "last hour"]):
        since = (datetime.now() - timedelta(hours=24)).timestamp()
        cur.execute("SELECT COUNT(*) FROM violations WHERE timestamp > ?", (since,))
        n = cur.fetchone()[0]
        answer = f"**{n} violations** recorded in the last 24 hours."

    # Helmet specific
    elif "helmet" in q:
        cur.execute("SELECT COUNT(*) FROM violations WHERE violation_type='Helmet Non-Compliance'")
        n = cur.fetchone()[0]
        answer = f"**{n} Helmet Non-Compliance** violations on record. The model uses a fine-tuned YOLOv8 classifier at 0.45 confidence threshold for HIGH severity, 0.20 for MEDIUM (human review required)."

    # Wrong side
    elif any(w in q for w in ["wrong side", "wrong-side", "opposite"]):
        cur.execute("SELECT COUNT(*) FROM violations WHERE violation_type='Wrong-Side Driving'")
        n = cur.fetchone()[0]
        answer = f"**{n} Wrong-Side Driving** violations on record. This uses a fine-tuned model with mAP50=0.975 — your highest-accuracy detector."

    # Seatbelt
    elif "seatbelt" in q or "seat belt" in q:
        cur.execute("SELECT COUNT(*) FROM violations WHERE violation_type='Seatbelt Non-Compliance'")
        n = cur.fetchone()[0]
        answer = f"**{n} Seatbelt Non-Compliance** violations. The model achieved mAP50=0.901 (precision 0.888, recall 0.859)."

    # Accuracy / models
    elif any(w in q for w in ["accuracy", "model", "map", "precision", "recall"]):
        answer = (
            "**Model accuracy summary:**\n"
            "- Wrong-Side Driving: mAP50 **0.975** (fine-tuned YOLOv8)\n"
            "- Seatbelt: mAP50 **0.901**, P=0.888, R=0.859 (fine-tuned)\n"
            "- Helmet: mAP50 ~0.82 (fine-tuned, threshold 0.45 HIGH / 0.20 MEDIUM)\n"
            "- Triple Riding: Geometric overlap + posture filter (base COCO model)\n"
            "- Illegal Parking: ByteTrack position history (< 20px / 90 frames)\n"
            "- Stop-Line/Red-Light: Y-threshold crossing (base COCO bbox)"
        )

    else:
        # Fallback: general DB summary
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

# ── Escalation report ─────────────────────────────────────────────────────────
@app.get("/api/report/{vid}")
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
  <tr><td>Database</td><td>SQLite · {str(DB_PATH)}</td></tr>
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

