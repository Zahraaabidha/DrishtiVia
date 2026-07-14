# DrishtiVia — AI Traffic Violation Detection System

DrishtiVia (Sanskrit: *दृष्टि* — vision) is a production-grade traffic violation detection system built for Bengaluru's road network. It combines YOLOv8s object detection, ByteTrack multi-object tracking, and three fine-tuned violation classifiers to automatically identify, classify, and document traffic violations from camera feeds and uploaded footage.

---

## Screenshots

| Live Detection | Review Queue | Analytics |
|---|---|---|
| Vehicle IDs + violation overlays drawn server-side | Filter by type / severity / plate | Bangalore hotspot map + trends |

---

## Features

### Detection Pipeline
- **7 violation types** detected automatically:
  - Helmet Non-Compliance (fine-tuned YOLOv8s, mAP50 ~0.85)
  - Seatbelt Non-Compliance (fine-tuned YOLOv8s, mAP50 0.901)
  - Wrong-Side Driving (fine-tuned YOLOv8s, mAP50 0.975)
  - Triple Riding (geometric + posture filter, base COCO model)
  - Stop-Line Violation (calibrated line crossing)
  - Red-Light Violation (stop-line + signal state)
  - Illegal Parking (ByteTrack position history)

- **CLAHE + dark-channel dehazing** preprocessing for rain, dust, night, and fog
- **ByteTrack** multi-object tracking with stable vehicle IDs (V-01, V-02 ...) per session
- **Temporal 2-sighting confirmation** — a violation must appear in ≥2 frames (or ≥65% confidence) before it is confirmed, eliminating single-frame false positives
- **Individual vehicle IDs** assigned to every detected vehicle; each violation is linked to its vehicle

### Frontend (React + Vite)
| Page | What it does |
|---|---|
| **Dashboard** | Live stats — total violations, pending review, top types, camera hotspots |
| **Live Analysis** | Upload image or video; see annotated output with vehicle IDs and violation boxes in real time via SSE canvas streaming; Vehicle Session Log table shows every vehicle and its violations |
| **Review Queue** | Operator review with filters (type / severity / plate / sort), pagination, snapshot evidence, confirm / dismiss / escalate actions |
| **Analytics** | Violation trends (7/14/30 days), repeat offender table, Bangalore hotspot map (Leaflet.js) |
| **Knowledge Graph** | Force-directed graph linking plates → cameras → violation types |
| **AI Agent** | Natural-language Q&A over violation data; uses Ollama (llama3/mistral) if running locally, falls back to rule-based |
| **Model Performance** | mAP50 / Precision / Recall / training images for all three fine-tuned models with radar charts |
| **Verify Evidence** | Cryptographic hash verification of stored evidence records |

---

## Architecture

```
DrishtiVia/
├── api.py                  # FastAPI backend — all endpoints
├── detect_core.py          # Pure Python detection pipeline (no Streamlit)
├── app.py                  # Legacy Streamlit version (backup only)
├── evidence_store/
│   ├── violations.db       # SQLite — 13-column violations table
│   └── snapshots/          # Full-frame + vehicle-crop JPEGs
├── runs/detect/runs/
│   ├── helmet_train/violavision_v1/weights/best.pt
│   ├── seatbelt_train/violavision_seatbelt_v1-2/weights/best.pt
│   └── wrongside_train/violavision_wrongside_v1/weights/best.pt
└── frontend/               # Vite + React + TypeScript + Tailwind
    └── src/
        ├── api/client.ts   # All API calls
        ├── pages/          # One file per page
        └── components/     # AppLayout, search, nav
```

**Request flow:**
```
Browser (React) → FastAPI (api.py) → detect_core.py → YOLOv8s + fine-tuned models
                                   → SQLite (evidence_store/violations.db)
                                   → SSE stream (base64 JPEG frames + violation events)
```

---

## Model Performance

| Model | Task | mAP@50 | Precision | Recall | Training Images |
|---|---|---|---|---|---|
| Helmet | With / Without helmet | 85.2% | 80.1% | 77.9% | 629 |
| Seatbelt | With / Without seatbelt | 90.1% | 88.8% | 85.9% | 660 |
| Wrong-Side | Wrong-side driving | 97.5% | 95.7% | 95.8% | 608 |

Base vehicle detection uses **YOLOv8s** (COCO, 11.2M parameters) running in tracking mode via ByteTrack.

---

## Setup & Installation

### Prerequisites
- Python 3.10+
- Node.js 18+
- Git

### 1. Clone the repository
```bash
git clone https://github.com/Zahraaabidha/DrishtiVia.git
cd DrishtiVia
```

### 2. Install Python dependencies
```bash
pip install fastapi uvicorn ultralytics opencv-python-headless easyocr numpy requests
```

> **Optional but recommended:** `pip install cryptography` for evidence signing

### 3. Add model weights
The `.pt` files are excluded from this repo (too large for GitHub). Place them at these exact paths:
```
runs/detect/runs/helmet_train/violavision_v1/weights/best.pt
runs/detect/runs/seatbelt_train/violavision_seatbelt_v1-2/weights/best.pt
runs/detect/runs/wrongside_train/violavision_wrongside_v1/weights/best.pt
```

The base YOLOv8s model (`yolov8s.pt`) is downloaded automatically by Ultralytics on first run.

> If you don't have the fine-tuned weights, the system still works — it falls back to the base COCO model with heuristic violation detection.

### 4. Initialise the database
```bash
mkdir -p evidence_store/snapshots
python - <<'EOF'
import sqlite3
con = sqlite3.connect("evidence_store/violations.db")
con.execute("""
  CREATE TABLE IF NOT EXISTS violations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL, plate_number TEXT, violation_type TEXT,
    confidence REAL, bbox TEXT, evidence_hash TEXT,
    camera_id TEXT, priority_score REAL, priority_level TEXT,
    operator_action TEXT, snapshot_path TEXT, vehicle_category TEXT
  )
""")
con.commit()
EOF
```

### 5. Install frontend dependencies
```bash
cd frontend
npm install
cd ..
```

### 6. Run both servers

**Terminal 1 — Backend:**
```bash
uvicorn api:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

Open **http://localhost:5173** in your browser.

---

## Usage Guide

### Analysing an image
1. Go to **Live Analysis** → select **Image** tab
2. Configure scene type (Junction / Highway / Parking Area)
3. Toggle violation flags if needed (stop-line, wrong-side, signal state)
4. Upload any traffic image → click **Run Detection**
5. Annotated output appears with vehicle IDs (V-01, V-02 ...) and violation labels

### Analysing a video (live streaming)
1. Go to **Live Analysis** → select **Video** tab
2. Set frame skip (6 = every 6th frame, faster; 3 = more thorough)
3. Upload MP4/AVI/MOV file → click **Analyse Video (Live)**
4. Watch the annotated canvas stream in real time — bounding boxes drawn server-side
5. **Vehicle Session Log** table below the canvas shows every vehicle detected and all confirmed violations
6. Confirmed violations panel updates live as violations are confirmed

### Reviewing violations
1. Go to **Review Queue**
2. Filter by violation type, severity (CRITICAL / HIGH / MEDIUM / LOW), plate number
3. Sort newest or oldest first
4. Click any row to open the detail modal with:
   - Full-frame snapshot + vehicle crop
   - Confidence score, bounding box, camera, timestamp
   - **Confirm / Dismiss / Escalate** actions
   - **Generate Report** — opens a printable HTML escalation report

### AI Agent
1. Go to **AI Agent**
2. Ask natural-language questions about your violation data, e.g.:
   - *"Which camera has the most violations this week?"*
   - *"How many helmet violations were detected today?"*
   - *"List all CRITICAL violations from Silk Board Junction"*
3. Requires [Ollama](https://ollama.ai) running locally with llama3 or mistral for full LLM responses; falls back to rule-based SQL answers automatically

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | System health, model availability |
| GET | `/api/stats` | Total / pending / confirmed counts |
| GET | `/api/violations` | Paginated violations with filters |
| POST | `/api/violations/{id}/action` | Confirm / dismiss / escalate |
| POST | `/api/detect/image` | Detect violations in a single image |
| POST | `/api/detect/video/upload` | Upload video, get session ID |
| GET | `/api/detect/video/stream/{sid}` | SSE stream — frames + violations |
| GET | `/api/analytics` | Trend data, repeat offenders, hotspots |
| GET | `/api/graph` | Knowledge graph data |
| POST | `/api/agent` | AI agent natural-language query |
| GET | `/api/report/{id}` | Printable HTML escalation report |
| POST | `/api/verify` | Verify evidence hash |
| GET | `/api/snapshot/{hash}/{kind}` | Serve evidence snapshot image |
| GET | `/api/search` | Full-text search across violations |

### Key query parameters for `/api/violations`
```
status          pending | confirmed | escalated | all
violation_type  Helmet Non-Compliance | Wrong-Side Driving | ...
severity        CRITICAL,HIGH (comma-separated)
plate           KA01AB1234 (partial match)
sort            newest | oldest
limit           default 50
offset          for pagination
```

---

## Configuration

Detection behaviour is controlled per-request via query parameters:

| Parameter | Default | Description |
|---|---|---|
| `frame_skip` | 6 | Process every Nth frame (lower = more thorough but slower) |
| `max_seconds` | 60 | Maximum video duration to analyse |
| `stop_line_y` | 400 | Y-pixel coordinate of the stop line |
| `signal_red` | false | Whether the traffic signal is currently red |
| `stopline_enabled` | false | Enable stop-line / red-light detection |
| `wrong_side_present` | false | Enable wrong-side heuristic fallback |
| `scene_type` | Junction | Junction / Highway / Parking Area |
| `flow_direction` | Left -> Right | Expected vehicle flow direction |

---

## Tech Stack

**Backend**
- Python 3.10+
- FastAPI + Uvicorn (async ASGI)
- Ultralytics YOLOv8s (COCO base + 3 fine-tuned)
- OpenCV (preprocessing, annotation, video I/O)
- EasyOCR (licence plate recognition)
- SQLite (evidence storage)
- Server-Sent Events (SSE) for real-time frame streaming

**Frontend**
- React 18 + TypeScript
- Vite
- Tailwind CSS
- Recharts (analytics charts, radar charts)
- Leaflet.js (Bangalore hotspot map)
- Axios

**Models**
- YOLOv8s — Ultralytics (COCO pretrained)
- Custom helmet dataset — 629 training images
- Custom seatbelt dataset — 660 training images
- Custom wrong-side dataset — 608 training images

---

## Training Your Own Models

Training scripts are included:

```bash
# Helmet model
python train_helmet.py

# Seatbelt model
python train_seatbelt.py

# Wrong-side model
python train_wrongside.py
```

Each script expects a YOLO-format dataset in `datasets/`. Results are saved to `runs/detect/runs/`.

---

## Known Limitations

- Licence plate OCR accuracy is limited on Indian plates in low-resolution or motion-blurred footage; plates frequently read as UNREADABLE
- Triple Riding detection uses a geometric overlap heuristic and may under-detect at elevated CCTV angles where persons appear above (not overlapping) the motorcycle
- Stop-line and red-light detection require manual calibration of the `stop_line_y` pixel coordinate per camera
- Wrong-side detection with the heuristic fallback (no fine-tuned model) can produce false positives at complex junctions
- Processing speed on CPU: approximately 1-2 seconds per frame at 640px with all three fine-tuned models active

---

## Project Structure

```
DrishtiVia/
├── README.md
├── .gitignore
├── api.py                          # FastAPI — all endpoints, SSE streaming
├── detect_core.py                  # Detection pipeline, annotation, ID assignment
├── app.py                          # Legacy Streamlit app (reference only)
├── train_helmet.py                 # Helmet model training script
├── train_seatbelt.py               # Seatbelt model training script
├── train_wrongside.py              # Wrong-side model training script
├── evidence_store/
│   ├── violations.db               # SQLite database (gitignored)
│   └── snapshots/                  # Evidence images (gitignored)
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.js
    └── src/
        ├── App.tsx                 # Router
        ├── api/client.ts           # API client + TypeScript interfaces
        ├── components/
        │   └── layout/AppLayout.tsx   # Sidebar nav, search
        └── pages/
            ├── DashboardPage.tsx
            ├── LiveDetectPage.tsx  # Image + video detection, session log
            ├── ReviewPage.tsx      # Operator review queue with filters
            ├── AnalyticsPage.tsx   # Charts + Bangalore map
            ├── KnowledgeGraphPage.tsx
            ├── AgentPage.tsx       # Ollama AI agent chat
            ├── ModelPerformancePage.tsx
            └── VerifyPage.tsx
```

