"""
seed_demo.py — Pre-seeds the SQLite DB with realistic demo violations.
Run once during Docker build so the dashboard is never empty.
Safe to re-run: skips seeding if data already exists.
"""
import sqlite3, hashlib, random, time
from pathlib import Path

DB_PATH = Path("evidence_store/violations.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

con = sqlite3.connect(str(DB_PATH))
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
con.commit()

existing = con.execute("SELECT COUNT(*) FROM violations").fetchone()[0]
if existing >= 10:
    print(f"DB already has {existing} violations — skipping seed.")
    con.close()
    exit(0)

VIOLATION_TYPES = [
    ("Helmet Non-Compliance",   "HIGH",     0.72, 0.88),
    ("Wrong-Side Driving",      "CRITICAL", 0.81, 0.95),
    ("Seatbelt Non-Compliance", "HIGH",     0.65, 0.90),
    ("Triple Riding",           "HIGH",     0.70, 0.85),
    ("Red-Light Violation",     "CRITICAL", 0.85, 0.97),
    ("Stop-Line Violation",     "HIGH",     0.78, 0.92),
    ("Illegal Parking",         "LOW",      0.55, 0.75),
]

CAMERAS = [
    "silk_board_junction",
    "kr_circle",
    "hebbal_flyover",
    "marathahalli_bridge",
    "whitefield_01",
]

PLATES = [
    "KA01AB1234", "KA05CD5678", "KA03EF9012", "KA51GH3456",
    "KA04IJ7890", "MH12KL2345", "TN09MN6789", "KA01AB1234",  # repeat offender
    "KA05CD5678", "KA01AB1234", "UNREADABLE", "UNREADABLE",
    "KA19PQ1111", "KA22RS2222", "DL01TU3333",
]

ACTIONS = [None, None, None, "CONFIRMED", "CONFIRMED", "ESCALATED", "DISMISSED"]
PRIORITY_MAP = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}

now = time.time()
rows = []
random.seed(42)

for i in range(60):
    vtype, severity, conf_lo, conf_hi = random.choice(VIOLATION_TYPES)
    conf      = round(random.uniform(conf_lo, conf_hi), 2)
    camera    = random.choice(CAMERAS)
    plate     = random.choice(PLATES)
    ts        = now - random.uniform(0, 7 * 86400)   # last 7 days
    ev_hash   = hashlib.sha256(f"{vtype}{camera}{plate}{ts}{i}".encode()).hexdigest()
    p_score   = round(PRIORITY_MAP.get(severity, 1) * conf * 10, 2)
    action    = random.choice(ACTIONS)
    vid       = f"V-{random.randint(1, 20):02d}"
    bbox      = [random.randint(50, 400), random.randint(50, 300),
                 random.randint(420, 900), random.randint(320, 600)]
    desc      = f"{vid}: {vtype} detected at {camera} (conf {conf:.0%})."

    rows.append((
        ts, plate, vtype, conf, p_score, severity,
        ev_hash, camera, action, None, None, None, desc, vid, str(bbox)
    ))

con.executemany("""
    INSERT INTO violations
        (timestamp, plate_number, violation_type, confidence, priority_score,
         priority_level, evidence_hash, camera_id, operator_action,
         operator_timestamp, dismissal_reason, snapshot_path, description,
         vehicle_id, bbox)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
""", rows)
con.commit()
con.close()
print(f"Seeded {len(rows)} demo violations into {DB_PATH}")
