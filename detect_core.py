"""
detect_core.py -- Pure-Python detection with ZERO Streamlit dependency.
Returns violations + per-vehicle IDs. Imported by api.py (FastAPI).
"""
import cv2
import numpy as np
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path

# ── preprocessing ──────────────────────────────────────────────────────────────
def preprocess(frame: np.ndarray, enable: bool = True) -> np.ndarray:
    if not enable:
        return frame
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    l = clahe.apply(l)
    frame = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)
    dark = np.min(frame, axis=2).astype(np.float32)
    atm  = float(np.percentile(dark, 95)) + 1e-6
    t    = np.clip(1.0 - 0.75 * dark / atm, 0.3, 1.0)
    out  = frame.astype(np.float32)
    for c in range(3):
        out[:, :, c] = np.clip((out[:, :, c] - atm) / t + atm, 0, 255)
    return out.astype(np.uint8)

# ── geometry helpers ──────────────────────────────────────────────────────────
def bbox_iou_overlap(b1, b2) -> float:
    ix1 = max(b1[0], b2[0]); iy1 = max(b1[1], b2[1])
    ix2 = min(b1[2], b2[2]); iy2 = min(b1[3], b2[3])
    if ix2 < ix1 or iy2 < iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    area1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
    return inter / (area1 + 1e-6)

def person_on_motorcycle(person_bbox, bike_bbox, tolerance: int = 40) -> bool:
    px_c = (person_bbox[0] + person_bbox[2]) / 2
    bx_c = (bike_bbox[0]  + bike_bbox[2])  / 2
    bw   = bike_bbox[2] - bike_bbox[0]
    horizontal_ok = abs(px_c - bx_c) < bw / 2 + tolerance

    # Rider's body must substantially overlap with the bike bounding box
    person_bottom = person_bbox[3]
    bike_top      = bike_bbox[1]
    bike_bottom   = bike_bbox[3]
    bike_height   = bike_bottom - bike_top
    # Person's bottom must be within the bike's vertical range (not just nearby)
    vertical_ok = bike_top - bike_height * 0.3 < person_bottom < bike_bottom + bike_height * 0.4

    overlap_ok = bbox_iou_overlap(person_bbox, bike_bbox) > 0.05

    return horizontal_ok and (overlap_ok or vertical_ok)

def extract_geometric_features(bbox, img_shape) -> dict:
    x1, y1, x2, y2 = bbox
    img_h, img_w   = img_shape[:2]
    w  = x2 - x1; h = y2 - y1
    cx = (x1 + x2) / 2; cy = (y1 + y2) / 2
    return {
        "aspect_ratio":      round(w / (h + 1e-6), 3),
        "norm_x":            round(cx / img_w, 3),
        "norm_y":            round(cy / img_h, 3),
        "norm_area":         round((w * h) / (img_w * img_h), 4),
        "bottom_frac":       round(y2 / img_h, 3),
        "is_riding_posture": (0.3 < (h / (w + 1e-6)) < 2.8),
    }

# ── helmet classifier ─────────────────────────────────────────────────────────
def classify_helmet(person_bbox, frame_bgr: np.ndarray, helmet_model):
    """
    Classify helmet status on a person/vehicle crop.
    Returns (class_name, confidence) or (None, 0.0).
    """
    x1, y1, x2, y2 = [int(c) for c in person_bbox]
    h = y2 - y1
    # Top 45% of person = head region; for full bike crop, use whole crop
    head_y2 = y1 + max(int(h * 0.45), 20)
    crop = frame_bgr[max(0, y1):head_y2, max(0, x1):x2]
    if crop.size == 0 or crop.shape[0] < 8 or crop.shape[1] < 8:
        # Retry: use the full bbox if head crop is too small
        crop = frame_bgr[max(0, y1):y2, max(0, x1):x2]
    if crop.size == 0:
        return None, 0.0
    if min(crop.shape[:2]) < 80:
        scale = max(2, int(96 / max(min(crop.shape[:2]), 1)))
        crop  = cv2.resize(crop, None, fx=scale, fy=scale,
                           interpolation=cv2.INTER_CUBIC)
    results = helmet_model(crop, conf=0.20, verbose=False)
    boxes   = results[0].boxes
    if not boxes:
        return None, 0.0
    names = results[0].names
    best  = max(boxes, key=lambda bx: float(bx.conf))
    return names[int(best.cls)], float(best.conf)

# ── plate-colour -> vehicle category ──────────────────────────────────────────
def classify_plate_category(vehicle_crop: np.ndarray) -> str:
    if vehicle_crop is None or vehicle_crop.size == 0:
        return "Unknown"
    hsv     = cv2.cvtColor(vehicle_crop, cv2.COLOR_BGR2HSV)
    avg_hue = float(np.mean(hsv[:, :, 0]))
    avg_sat = float(np.mean(hsv[:, :, 1]))
    avg_val = float(np.mean(hsv[:, :, 2]))
    if avg_sat < 40 and avg_val > 180:
        return "Private (White plate)"
    elif 20 < avg_hue < 35 and avg_sat > 100:
        return "Commercial (Yellow plate)"
    elif 60 < avg_hue < 90 and avg_sat > 80:
        return "Electric Vehicle (Green plate)"
    elif 90 < avg_hue < 130 and avg_sat > 80:
        return "Government (Blue plate)"
    else:
        return "Unclassified"

# ── stationary vehicle tracker ────────────────────────────────────────────────
_vehicle_positions: dict = defaultdict(lambda: deque(maxlen=90))

def reset_tracking():
    _vehicle_positions.clear()

def is_stationary(track_id: int, bbox: list,
                  move_threshold_px: float = 20.0,
                  img_w: int = 1280,
                  park_min_frames: int = 60) -> bool:
    cx = (bbox[0] + bbox[2]) / 2
    cy = (bbox[1] + bbox[3]) / 2
    _vehicle_positions[track_id].append((cx, cy))
    history   = list(_vehicle_positions[track_id])
    norm_x    = cx / max(img_w, 1)
    near_edge = norm_x < 0.20 or norm_x > 0.80
    min_frames = 25 if near_edge else park_min_frames
    if len(history) < min_frames:
        return False
    xs = [p[0] for p in history]
    ys = [p[1] for p in history]
    return ((max(xs) - min(xs))**2 + (max(ys) - min(ys))**2) ** 0.5 < move_threshold_px

# ── ID assignment ─────────────────────────────────────────────────────────────
# Maps ByteTrack ID (or a bbox-hash for image mode) -> stable string "V-01"
_id_map: dict = {}
_id_counter: list = [0]

def reset_id_map():
    _id_map.clear()
    _id_counter[0] = 0

def get_vehicle_id(track_id, bbox) -> str:
    """Returns a stable short ID like 'V-01'. Uses track_id when available."""
    if track_id is not None:
        key = ("tid", track_id)
    else:
        # For images: bucket bbox to nearest 20px to tolerate minor jitter
        key = ("bbox",
               round(bbox[0] / 20) * 20,
               round(bbox[1] / 20) * 20,
               round(bbox[2] / 20) * 20,
               round(bbox[3] / 20) * 20)
    if key not in _id_map:
        _id_counter[0] += 1
        _id_map[key] = f"V-{_id_counter[0]:02d}"
    return _id_map[key]

# ── annotation ────────────────────────────────────────────────────────────────
VIOLATION_LABEL = {
    "Helmet Non-Compliance":   "No Helmet",
    "Triple Riding":           "Triple Riding",
    "Red-Light Violation":     "Red Light",
    "Stop-Line Violation":     "Stop Line",
    "Wrong-Side Driving":      "Wrong Side",
    "Illegal Parking":         "Parking",
    "Seatbelt Non-Compliance": "No Seatbelt",
}

SEVERITY_COLOR = {
    "CRITICAL": (0,   0,   210),   # red
    "HIGH":     (0,   100, 255),   # orange-red
    "MEDIUM":   (20,  160, 255),   # orange
    "LOW":      (50,  200, 80),    # green
}

VEHICLE_ID_COLOR  = (40, 40, 40)     # near-black box for vehicle ID labels
VEHICLE_BOX_COLOR = (130, 130, 130)  # grey border for non-violating vehicles

def annotate(frame: np.ndarray, violations: list, vehicles: list | None = None) -> np.ndarray:
    """
    Draw individual vehicle IDs on all detected vehicles, then overlay
    violation boxes with violation type + confidence on violating ones.

    vehicles: list of dicts with keys: id, bbox, cls
    violations: list of dicts from detect_violations()
    """
    out  = frame.copy()
    font = cv2.FONT_HERSHEY_SIMPLEX

    # Build set of violating vehicle IDs for quick lookup
    violation_vid_set = {v.get("vehicle_id") for v in violations if v.get("vehicle_id")}

    # ── 1. Draw all vehicles with their ID label ───────────────────────────────
    if vehicles:
        for veh in vehicles:
            x1, y1, x2, y2 = [int(c) for c in veh["bbox"]]
            vid = veh["id"]
            is_violator = vid in violation_vid_set

            # Violating vehicles get a bold coloured border; clean vehicles get grey
            box_color = (0, 60, 200) if is_violator else VEHICLE_BOX_COLOR
            box_thick = 2 if is_violator else 1
            cv2.rectangle(out, (x1, y1), (x2, y2), box_color, box_thick)

            # ID tag (bottom-left of box so it doesn't clash with violation label at top)
            id_label = vid
            (tw, th), bl = cv2.getTextSize(id_label, font, 0.38, 1)
            tag_y = y2  # anchor to bottom of box
            cv2.rectangle(out, (x1, tag_y - th - bl - 2), (x1 + tw + 6, tag_y + 2),
                          VEHICLE_ID_COLOR, -1)
            cv2.putText(out, id_label, (x1 + 3, tag_y - bl - 1),
                        font, 0.38, (255, 255, 255), 1, cv2.LINE_AA)

    # ── 2. Draw violation overlays (bold, coloured, labelled) ─────────────────
    seen_boxes: list = []  # avoid stacking duplicate labels at same position
    for v in violations:
        x1, y1, x2, y2 = [int(c) for c in v["bbox"]]
        col = SEVERITY_COLOR.get(v.get("severity", "LOW"), (50, 200, 80))

        cv2.rectangle(out, (x1, y1), (x2, y2), col, 3)

        short   = VIOLATION_LABEL.get(v["type"], v["type"])
        vid_tag = v.get("vehicle_id", "")
        label   = f"{vid_tag} | {short} {v['confidence']:.0%}"
        (tw, th), bl = cv2.getTextSize(label, font, 0.44, 1)

        # Stack labels upward if two violations overlap at the same x
        base_y = y1 - th - bl - 4
        for sy in seen_boxes:
            if abs(base_y - sy) < th + 6 and abs(x1 - sy) < tw:
                base_y = sy - th - 6
        by = max(base_y, 18)
        seen_boxes.append(by)

        overlay = out.copy()
        cv2.rectangle(overlay, (x1, by), (x1 + tw + 10, by + th + bl + 4), col, -1)
        cv2.addWeighted(overlay, 0.82, out, 0.18, 0, out)
        cv2.putText(out, label, (x1 + 5, by + th + 1),
                    font, 0.44, (255, 255, 255), 1, cv2.LINE_AA)

    # ── 3. Banner + violation count ────────────────────────────────────────────
    banner = f"DrishtiVia  |  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    bw, bh = cv2.getTextSize(banner, font, 0.40, 1)[0]
    cv2.rectangle(out, (0, 0), (bw + 12, bh + 10), (12, 12, 12), -1)
    cv2.putText(out, banner, (6, bh + 4), font, 0.40, (200, 200, 200), 1, cv2.LINE_AA)

    n = len(violations)
    if n:
        badge = f"  {n} VIOLATION{'S' if n > 1 else ''}  "
        bw2, bh2 = cv2.getTextSize(badge, font, 0.42, 1)[0]
        cv2.rectangle(out, (0, bh + 12), (bw2 + 12, bh + bh2 + 24), (0, 0, 190), -1)
        cv2.putText(out, badge, (6, bh + bh2 + 18), font, 0.42, (255, 255, 255), 1, cv2.LINE_AA)

    return out

# ── main detection pipeline ───────────────────────────────────────────────────
def detect_violations(
    results,
    stop_line_y:        int   = 400,
    img_shape:          tuple = (720, 1280),
    frame_bgr:          np.ndarray | None = None,
    helmet_model               = None,
    seatbelt_model             = None,
    wrongside_model            = None,
    signal_red:         bool  = False,
    stopline_enabled:   bool  = False,
    scene_type:         str   = "Junction",
    wrong_side_present: bool  = False,
    flow_direction:     str   = "Left -> Right",
    park_min_frames:    int   = 60,
) -> dict:
    """
    Returns {"violations": [...], "vehicles": [...]}

    Each vehicle gets a stable ID (V-01, V-02 ...).
    Violations reference their vehicle via "vehicle_id".
    """
    names   = results[0].names
    boxes   = results[0].boxes
    box_ids = (boxes.id.int().tolist()
               if getattr(boxes, "id", None) is not None
               else [None] * len(boxes))

    # ── Parse all detections and assign vehicle IDs ───────────────────────────
    VEHICLE_CLASSES = {"motorcycle", "car", "truck", "bus", "bicycle", "auto rickshaw", "auto"}
    PERSON_CLASSES  = {"person"}

    all_dets  = []   # (bbox, cls, conf, track_id, vehicle_id)
    vehicles  = []   # [{"id": "V-01", "bbox": ..., "cls": ...}]

    for j, box in enumerate(boxes):
        cls_name = names[int(box.cls)]
        conf     = float(box.conf)
        if conf < 0.12:
            continue
        tid  = box_ids[j] if j < len(box_ids) else None
        bbox = box.xyxy[0].tolist()
        vid  = get_vehicle_id(tid, bbox) if cls_name in VEHICLE_CLASSES else None
        all_dets.append((bbox, cls_name, conf, tid, vid))
        if cls_name in VEHICLE_CLASSES:
            vehicles.append({"id": vid, "bbox": bbox, "cls": cls_name, "conf": conf})
        elif cls_name in PERSON_CLASSES:
            pass  # persons tracked separately below

    motorcycles = [(b, c, t, v) for b, cls, c, t, v in all_dets if cls == "motorcycle"]
    persons     = [(b, c, t)    for b, cls, c, t, v in all_dets if cls in PERSON_CLASSES]
    all_vehicles= [(b, c, t, v) for b, cls, c, t, v in all_dets if cls in VEHICLE_CLASSES]
    cars        = [(b, c, t, v) for b, cls, c, t, v in all_dets if cls == "car"]

    violations: list[dict] = []

    # ── 1. Helmet Non-Compliance ──────────────────────────────────────────────
    for bike_bbox, bike_conf, bike_tid, bike_vid in motorcycles:
        riders = [(p, pc) for p, pc, pt in persons
                  if person_on_motorcycle(p, bike_bbox)]

        if not riders:
            # No rider visible — skip entirely rather than generating a false flag.
            # The motorcycle bounding box is a chassis crop; running the helmet model
            # on it produces meaningless results (it's trained on human head crops).
            continue

        # Riders confirmed on the bike — check each one
        for person_bbox, person_conf in riders:
            geo = extract_geometric_features(person_bbox, img_shape)

            # Require a plausible riding posture: person height > width (sitting upright)
            p_w = person_bbox[2] - person_bbox[0]
            p_h = person_bbox[3] - person_bbox[1]
            if p_w > 0 and (p_h / p_w) < 0.8:
                # Too wide relative to height — more likely a lying/crouching pedestrian
                continue

            if helmet_model is not None and frame_bgr is not None:
                cls_name, helm_conf = classify_helmet(person_bbox, frame_bgr, helmet_model)
                if cls_name and "with" in cls_name.lower() and helm_conf >= 0.35:
                    pass  # helmeted — no violation
                elif cls_name and "without" in cls_name.lower() and helm_conf >= 0.35:
                    violations.append({
                        "type":        "Helmet Non-Compliance",
                        "confidence":  round(helm_conf, 2),
                        "bbox":        person_bbox,
                        "track_id":    bike_tid,
                        "vehicle_id":  bike_vid,
                        "severity":    "HIGH" if helm_conf >= 0.55 else "MEDIUM",
                        "description": f"Rider on {bike_vid} WITHOUT helmet (conf {helm_conf:.0%}).",
                        "geo_features": geo,
                    })
                # else: inconclusive — do not flag; let the 2-sighting filter catch repeats
            else:
                violations.append({
                    "type":        "Helmet Non-Compliance",
                    "confidence":  round(min(bike_conf * 0.8, 0.70), 2),
                    "bbox":        bike_bbox,
                    "track_id":    bike_tid,
                    "vehicle_id":  bike_vid,
                    "severity":    "MEDIUM",
                    "description": f"Rider on {bike_vid} — helmet unverifiable (base model only).",
                    "geo_features": geo,
                })

    # ── 2. Triple Riding ──────────────────────────────────────────────────────
    for bike_bbox, bike_conf, bike_tid, bike_vid in motorcycles:
        bw        = bike_bbox[2] - bike_bbox[0]
        tight_tol = max(int(bw * 0.45), 30)
        riding_persons = []
        for p, _, _ in persons:
            geo = extract_geometric_features(p, img_shape)
            if person_on_motorcycle(p, bike_bbox, tolerance=tight_tol):
                riding_persons.append(p)
        if len(riding_persons) >= 3:
            violations.append({
                "type":        "Triple Riding",
                "confidence":  round(min(bike_conf + 0.04, 0.90), 2),
                "bbox":        bike_bbox,
                "track_id":    bike_tid,
                "vehicle_id":  bike_vid,
                "severity":    "HIGH",
                "description": f"{bike_vid}: {len(riding_persons)} riders detected on single motorcycle.",
            })

    # ── 3. Seatbelt Non-Compliance ────────────────────────────────────────────
    if seatbelt_model is not None and frame_bgr is not None:
        for car_bbox, car_conf, car_tid, car_vid in cars:
            x1, y1, x2, y2 = [int(c) for c in car_bbox]
            car_crop = frame_bgr[max(0, y1):y2, max(0, x1):x2]
            if car_crop.size == 0 or car_crop.shape[0] < 40 or car_crop.shape[1] < 40:
                continue
            # Upscale small crops so model has enough detail
            if min(car_crop.shape[:2]) < 120:
                scale = max(2, int(160 / max(min(car_crop.shape[:2]), 1)))
                car_crop = cv2.resize(car_crop, None, fx=scale, fy=scale,
                                      interpolation=cv2.INTER_CUBIC)
            sb_results = seatbelt_model(car_crop, conf=0.18, verbose=False)
            for r in sb_results[0].boxes:
                cls_name = sb_results[0].names[int(r.cls)]
                sb_conf  = float(r.conf)
                if "noseatbelt" in cls_name.lower() or "without" in cls_name.lower():
                    if sb_conf >= 0.18:
                        violations.append({
                            "type":        "Seatbelt Non-Compliance",
                            "confidence":  round(sb_conf, 2),
                            "bbox":        car_bbox,
                            "track_id":    car_tid,
                            "vehicle_id":  car_vid,
                            "severity":    "HIGH" if sb_conf >= 0.70 else "MEDIUM",
                            "description": f"{car_vid}: driver not wearing seatbelt (conf {sb_conf:.0%}).",
                        })
                        break

    # ── 4. Stop-Line / Red-Light Violation ────────────────────────────────────
    if stopline_enabled:
        seen_stopline = set()
        for v_bbox, v_conf, v_tid, v_vid in all_vehicles:
            vehicle_bottom = v_bbox[3]
            key = v_vid or (round(v_bbox[0] / 50), round(v_bbox[1] / 50))
            if vehicle_bottom > stop_line_y and key not in seen_stopline:
                seen_stopline.add(key)
                vtype = "Red-Light Violation" if signal_red else "Stop-Line Violation"
                violations.append({
                    "type":        vtype,
                    "confidence":  round(min(v_conf + 0.02, 0.97), 2),
                    "bbox":        v_bbox,
                    "track_id":    v_tid,
                    "vehicle_id":  v_vid,
                    "severity":    "CRITICAL" if signal_red else "HIGH",
                    "description": f"{v_vid}: crossed stop line"
                                   + (" while RED signal active." if signal_red else "."),
                })

    # ── 5. Wrong-Side Driving ─────────────────────────────────────────────────
    if wrongside_model is not None and frame_bgr is not None:
        seen_ws = set()
        for vb, vc, vt, vv in all_vehicles:
            x1, y1, x2, y2 = [int(c) for c in vb]
            v_crop = frame_bgr[max(0, y1):y2, max(0, x1):x2]
            if v_crop.size == 0 or v_crop.shape[0] < 40 or v_crop.shape[1] < 40:
                continue
            ws_res = wrongside_model(v_crop, conf=0.20, verbose=False)
            for r in ws_res[0].boxes:
                cls_name = ws_res[0].names[int(r.cls)]
                ws_conf  = float(r.conf)
                if "wrong" in cls_name.lower() and ws_conf >= 0.20:
                    key = vv or (tuple(int(c) // 40 for c in vb))
                    if key not in seen_ws:
                        seen_ws.add(key)
                        violations.append({
                            "type":        "Wrong-Side Driving",
                            "confidence":  round(ws_conf, 2),
                            "bbox":        vb,
                            "track_id":    vt,
                            "vehicle_id":  vv,
                            "severity":    "CRITICAL",
                            "description": f"{vv}: wrong-side driving detected (conf {ws_conf:.0%}).",
                        })
                    break
    elif wrong_side_present and all_vehicles and scene_type != "Parking Area":
        scored = []
        for vb, vc, vt, vv in all_vehicles:
            geo   = extract_geometric_features(vb, img_shape)
            score = geo["norm_x"] if "Right" in flow_direction else (1 - geo["norm_x"])
            scored.append((score, vb, vc, vt, vv, geo))
        scored.sort(key=lambda s: s[0])
        if scored:
            _, vb, vc, vt, vv, geo = scored[0]
            violations.append({
                "type":        "Wrong-Side Driving",
                "confidence":  round(min(vc + 0.03, 0.80), 2),
                "bbox":        vb,
                "track_id":    vt,
                "vehicle_id":  vv,
                "severity":    "CRITICAL",
                "description": f"{vv}: heuristic — vehicle at x={geo['norm_x']:.2f} against flow ({flow_direction}).",
                "geo_features": geo,
            })

    # ── 6. Illegal Parking ────────────────────────────────────────────────────
    if scene_type != "Highway":
        stopline_bboxes = {tuple(int(c) for c in v["bbox"]) for v in violations
                           if "Line" in v["type"] or "Light" in v["type"]}
        for v_bbox, v_conf, v_tid, v_vid in cars:
            if tuple(int(c) for c in v_bbox) in stopline_bboxes:
                continue
            geo    = extract_geometric_features(v_bbox, img_shape)
            parked = False
            if v_tid is not None:
                parked = is_stationary(v_tid, v_bbox,
                                       img_w=img_shape[1],
                                       park_min_frames=park_min_frames)
            else:
                # Single-image heuristic: near edge of frame and large
                parked = (geo["bottom_frac"] > 0.80 and geo["norm_area"] > 0.008
                          and (geo["norm_x"] < 0.18 or geo["norm_x"] > 0.82))
            if parked:
                violations.append({
                    "type":        "Illegal Parking",
                    "confidence":  round(v_conf * 0.85, 2),
                    "bbox":        v_bbox,
                    "track_id":    v_tid,
                    "vehicle_id":  v_vid,
                    "severity":    "LOW",
                    "description": (
                        f"{v_vid}: stationary >60 frames (position delta < 20px)."
                        if v_tid is not None else
                        f"{v_vid}: vehicle in shoulder/kerb zone (single-image heuristic)."
                    ),
                    "geo_features": geo,
                })

    return {"violations": violations, "vehicles": vehicles}
