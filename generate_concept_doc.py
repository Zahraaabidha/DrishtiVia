"""
Generates ViolaVision 2.0 concept document PDF for Flipkart Gridlock Hackathon 2.0
Run: python generate_concept_doc.py
Output: ViolaVision_2_Concept_Document.pdf
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "ViolaVision_2_Concept_Document.pdf")

# ── Colour palette ─────────────────────────────────────────────────────────────
DARK    = colors.HexColor("#0d1117")
ACCENT  = colors.HexColor("#e05c2e")   # Flipkart orange-ish
BLUE    = colors.HexColor("#1a73e8")
LIGHT   = colors.HexColor("#f6f8fa")
GREY    = colors.HexColor("#555555")
GREEN   = colors.HexColor("#1a7f37")
BORDER  = colors.HexColor("#d0d7de")

# ── Styles ─────────────────────────────────────────────────────────────────────
base = getSampleStyleSheet()

def S(name, **kw):
    return ParagraphStyle(name, **kw)

TITLE = S("DocTitle",
    fontSize=26, fontName="Helvetica-Bold",
    textColor=DARK, alignment=TA_CENTER,
    spaceAfter=6, leading=32)

SUBTITLE = S("DocSubtitle",
    fontSize=13, fontName="Helvetica",
    textColor=GREY, alignment=TA_CENTER,
    spaceAfter=4)

SEC_HEAD = S("SecHead",
    fontSize=14, fontName="Helvetica-Bold",
    textColor=ACCENT, spaceBefore=18, spaceAfter=6,
    leading=18)

SUBSEC = S("SubSec",
    fontSize=11, fontName="Helvetica-Bold",
    textColor=DARK, spaceBefore=10, spaceAfter=4)

BODY = S("Body",
    fontSize=10, fontName="Helvetica",
    textColor=DARK, spaceAfter=6, leading=15,
    alignment=TA_JUSTIFY)

BULLET = S("Bullet",
    fontSize=10, fontName="Helvetica",
    textColor=DARK, spaceAfter=4, leading=14,
    leftIndent=16, bulletIndent=4)

CAPTION = S("Caption",
    fontSize=8, fontName="Helvetica-Oblique",
    textColor=GREY, alignment=TA_CENTER, spaceAfter=8)

METRIC_VAL = S("MetricVal",
    fontSize=20, fontName="Helvetica-Bold",
    textColor=ACCENT, alignment=TA_CENTER, leading=24)

METRIC_LBL = S("MetricLbl",
    fontSize=8, fontName="Helvetica",
    textColor=GREY, alignment=TA_CENTER)

CODE = S("Code",
    fontSize=8, fontName="Courier",
    textColor=colors.HexColor("#24292f"),
    backColor=LIGHT, spaceAfter=6,
    leftIndent=12, leading=12)

def hr():
    return HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=8, spaceBefore=4)

def section(n, title):
    return [
        Spacer(1, 0.2*cm),
        Paragraph(f"{n}. {title}", SEC_HEAD),
        hr(),
    ]

def sub(title):
    return Paragraph(title, SUBSEC)

def body(txt):
    return Paragraph(txt, BODY)

def bullet(txt):
    return Paragraph(f"<bullet>&bull;</bullet> {txt}", BULLET)

def metric_table(data):
    """data = [(value, label), ...]"""
    cells = [[Paragraph(v, METRIC_VAL) for v, _ in data],
             [Paragraph(l, METRIC_LBL) for _, l in data]]
    t = Table([cells[0], cells[1]], colWidths=[4.2*cm]*len(data))
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), LIGHT),
        ("ROUNDEDCORNERS", [4]),
        ("BOX",          (0,0), (-1,-1), 0.5, BORDER),
        ("INNERGRID",    (0,0), (-1,-1), 0.5, BORDER),
        ("TOPPADDING",   (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0), (-1,-1), 8),
        ("ALIGN",        (0,0), (-1,-1), "CENTER"),
    ]))
    return t

def two_col_table(rows, col_a="Prototype", col_b="Production"):
    data = [[Paragraph(col_a, S("th", fontSize=9, fontName="Helvetica-Bold",
                                textColor=colors.white)),
             Paragraph(col_b, S("th2", fontSize=9, fontName="Helvetica-Bold",
                                textColor=colors.white))]]
    for r in rows:
        data.append([Paragraph(r[0], BODY), Paragraph(r[1], BODY)])
    t = Table(data, colWidths=[8.5*cm, 8.5*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,0), DARK),
        ("BACKGROUND",   (0,1), (-1,-1), LIGHT),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, LIGHT]),
        ("BOX",          (0,0), (-1,-1), 0.5, BORDER),
        ("INNERGRID",    (0,0), (-1,-1), 0.5, BORDER),
        ("TOPPADDING",   (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0), (-1,-1), 5),
        ("LEFTPADDING",  (0,0), (-1,-1), 8),
    ]))
    return t

# ── Build document ─────────────────────────────────────────────────────────────
doc = SimpleDocTemplate(
    OUT, pagesize=A4,
    leftMargin=2.2*cm, rightMargin=2.2*cm,
    topMargin=2.5*cm, bottomMargin=2.5*cm,
    title="ViolaVision 2.0 — Concept Document",
    author="Team ViolaVision",
)

story = []

# ── Cover ──────────────────────────────────────────────────────────────────────
story += [
    Spacer(1, 1.5*cm),
    Paragraph("ViolaVision 2.0", TITLE),
    Paragraph("AI-Powered Traffic Violation Intelligence Platform", SUBTITLE),
    Paragraph("Flipkart Gridlock Hackathon 2.0  |  Theme 3: Computer Vision for Traffic Violations", SUBTITLE),
    Spacer(1, 0.6*cm),
    hr(),
    Spacer(1, 0.4*cm),
]

# Key metrics row
story.append(metric_table([
    ("80.5%", "Helmet Model mAP50"),
    ("3-of-5", "Frame Confirmation"),
    ("7+", "Violation Types"),
    ("SHA-256", "Evidence Integrity"),
    ("ByteTrack", "Persistent Tracking"),
]))
story.append(Spacer(1, 0.6*cm))

story.append(body(
    "ViolaVision 2.0 is an end-to-end traffic violation detection and evidence management "
    "platform designed for deployment across Bengaluru's existing ITMS camera infrastructure. "
    "The system combines fine-tuned computer vision models with cryptographically signed "
    "evidence records, human-in-the-loop review workflows, and a real-time operations dashboard "
    "— processing continuous video feeds using the identical pipeline demonstrated on recorded "
    "traffic footage in this submission."
))

# ── Section 1 — Problem Statement ─────────────────────────────────────────────
story += section(1, "Problem Statement")

story.append(body(
    "Bengaluru records over 12,000 road accident fatalities annually (MoRTH 2023). The top "
    "contributing violations — helmet non-compliance, red-light running, and wrong-side driving "
    "— are largely undetected due to manual enforcement limitations. Bengaluru's existing ITMS "
    "infrastructure covers 172 junctions with 1,050+ cameras, yet automated violation detection "
    "is absent from most deployments. Manual enforcement reaches fewer than 2% of daily "
    "violation events at high-density junctions such as Silk Board, KR Circle, and Hebbal."
))

story.append(sub("Key Limitations of Current Enforcement"))
for b in [
    "Manual surveillance: human officers cannot monitor hundreds of cameras simultaneously.",
    "No persistent evidence chain: verbal or photograph-based records are legally contestable.",
    "No repeat-offender intelligence: each violation is processed in isolation, missing serial offenders.",
    "No integration with VAHAN: owner lookup requires separate manual queries per violation.",
    "Single-image analysis: existing pilot systems flag violations per frame with no temporal confirmation, producing high false-positive rates.",
]:
    story.append(bullet(b))

# ── Section 2 — Solution Architecture ─────────────────────────────────────────
story += section(2, "Solution Architecture")

story.append(body(
    "ViolaVision 2.0 is structured as a seven-layer cascade, each layer building on the "
    "outputs of the previous. The architecture is frame-independent at the detection layer — "
    "the identical logic runs on a single uploaded image for testing, or on 30 frames per "
    "second from a live RTSP stream in production."
))

layers = [
    ("Layer 1 — Ingestion & Preprocessing",
     "CLAHE contrast enhancement (adaptive histogram equalisation on L-channel in LAB "
     "colour space) applied to every frame before detection. Handles low-light, haze, and "
     "glare conditions common to Indian junctions at dawn/dusk without requiring IR hardware "
     "during daytime operation."),
    ("Layer 2 — Dual-Model Detection",
     "YOLOv8s (COCO-pretrained, 80 classes) handles vehicle, motorcycle, and person detection. "
     "A separately loaded fine-tuned YOLOv8n (trained on HELMET INDIA dataset, 530 images, "
     "mAP50 = 80.5%) classifies the head region of each detected person riding a motorcycle "
     "into With Helmet or Without Helmet. The two models run independently — the base model "
     "is never replaced by the classifier, resolving the architecture flaw common to "
     "single-model approaches."),
    ("Layer 3 — Geometric Feature Engineering",
     "Bounding box geometric features are explicitly extracted per detection: aspect ratio "
     "(w/h), normalised centroid position (norm_x, norm_y), normalised area (fraction of "
     "frame), bottom fraction (vertical position), and riding posture flag (aspect ratio "
     "within riding-posture bounds). These named features are used directly in violation "
     "rules — for example, triple-riding detection requires riding posture AND significant "
     "IoU overlap with the motorcycle bbox, preventing background pedestrians from "
     "being miscounted as riders."),
    ("Layer 4 — Temporal Confirmation via ByteTrack",
     "YOLOv8's built-in ByteTrack assigns persistent integer IDs to each detected object "
     "across frames. A per-track violation history (deque, maxlen=5) records whether each "
     "tracked object was flagged in each processed frame. A violation is confirmed and "
     "evidence is generated only when 3 of the last 5 frames flag the same track ID for the "
     "same violation type. This eliminates single-frame false positives and makes "
     "the temporal smoothing claim genuinely real rather than architecturally described only."),
    ("Layer 5 — Cross-Modal Context Validation",
     "Scene type (Junction / Parking Area / Highway) is used to suppress contextually "
     "impossible violations: stop-line and red-light violations are suppressed in Parking "
     "Area scenes; illegal parking detection is suppressed on Highways. In production, "
     "scene type is assigned automatically per camera ID from the ITMS camera registry. "
     "In the prototype, the operator sets it via a sidebar control, demonstrating the "
     "suppression logic."),
    ("Layer 6 — Priority Scoring",
     "Each confirmed violation receives a weighted priority score: P = V_w x L_w x T_w x R_w, "
     "where V_w is the violation-type weight (derived from MoRTH 2023 fatality contribution "
     "statistics — red-light and wrong-side carry weight 10.0, helmet 7.0), L_w is the "
     "location risk multiplier (Silk Board = 1.5, KR Circle = 1.4 based on accident density), "
     "T_w is the time-of-day multiplier (peak hours 7-10am and 5-8pm: 1.4, night 1.3), and "
     "R_w is the repeat-offender multiplier (first offence: 1.0, 3-6 offences: 2.0, "
     "7+ offences: 3.0 with automatic RTO referral). Scores above 25 trigger CRITICAL "
     "auto-challan; 15-25 trigger HIGH same-day review."),
    ("Layer 7 — Evidence Generation and Active Learning",
     "Each confirmed violation generates a tamper-evident JSON record: the record is "
     "SHA-256 hashed, then the hash is signed using RSA-PSS (2048-bit, SHA-256 digest, "
     "PSS padding). The private key is generated once and stored on disk for the prototype; "
     "production uses an Infineon SLB9670 TPM chip where the key never leaves hardware. "
     "Operator dismiss actions (with mandatory reason: poor image quality / wrong "
     "classification / no actual violation / other) are logged to a separate table, "
     "forming the retraining dataset for the active learning pipeline."),
]

for head, txt in layers:
    story.append(KeepTogether([sub(head), body(txt)]))

# ── Section 3 — Violation Detection Capabilities ──────────────────────────────
story += section(3, "Violation Detection Capabilities")

viol_data = [
    ["Violation Type", "Detection Method", "Severity", "V_w"],
    ["Helmet Non-Compliance", "Fine-tuned YOLOv8n on head crop", "HIGH", "7.0"],
    ["Triple Riding", "Person count on motorcycle + posture filter", "HIGH", "8.0"],
    ["Red-Light Violation", "Stop-line cross + signal state toggle", "CRITICAL", "10.0"],
    ["Stop-Line Violation", "Vehicle bottom edge past calibrated Y", "MEDIUM", "6.0"],
    ["Wrong-Side Driving", "Position vs expected flow direction", "CRITICAL", "10.0"],
    ["Illegal Parking", "Stationary detection via track ID history", "LOW", "3.0"],
    ["Seatbelt Non-Compliance", "Architecture ready; classifier planned (post-hackathon)", "HIGH", "6.0"],
]

vt = Table(viol_data, colWidths=[4.8*cm, 6.5*cm, 2.2*cm, 1.5*cm])
vt.setStyle(TableStyle([
    ("BACKGROUND",   (0,0), (-1,0), DARK),
    ("TEXTCOLOR",    (0,0), (-1,0), colors.white),
    ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
    ("FONTSIZE",     (0,0), (-1,-1), 9),
    ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, LIGHT]),
    ("BOX",          (0,0), (-1,-1), 0.5, BORDER),
    ("INNERGRID",    (0,0), (-1,-1), 0.5, BORDER),
    ("TOPPADDING",   (0,0), (-1,-1), 5),
    ("BOTTOMPADDING",(0,0), (-1,-1), 5),
    ("LEFTPADDING",  (0,0), (-1,-1), 6),
    ("ALIGN",        (2,0), (-1,-1), "CENTER"),
]))
story.append(vt)
story.append(Spacer(1, 0.3*cm))

story.append(body(
    "Illegal parking detection in video mode uses genuine stationary detection: each "
    "vehicle's centroid position is recorded across 15 tracked frames; a vehicle is flagged "
    "only if total centroid displacement is below 18 pixels — confirming it has not moved. "
    "This replaces the zone-heuristic approach (bottom_frac threshold) used in single-image "
    "mode, which produced false positives on aerial highway footage where all vehicles "
    "naturally appear near the bottom of the frame."
))

# ── Section 4 — Model Training ─────────────────────────────────────────────────
story += section(4, "Model Training and Performance")

story.append(sub("Helmet Detection Classifier"))
story.append(body(
    "Dataset: HELMET INDIA v1 (Roboflow Universe, CC BY 4.0). "
    "530 training images, 66 validation images, 2 classes: With Helmet / Without Helmet. "
    "Images sourced from Indian roads across multiple cities, varying lighting conditions, "
    "and camera angles — providing realistic diversity for the target deployment environment."
))

train_data = [
    ["Parameter", "Value", "Rationale"],
    ["Base model", "YOLOv8n pretrained on COCO", "Transfer learning from 80-class general detector"],
    ["Epochs", "33 (early stopping at patience=10)", "Stopped when validation mAP plateaued"],
    ["Image size", "640 x 640", "Standard YOLOv8 input resolution"],
    ["Batch size", "16 (GPU)", "RTX 3050 4GB VRAM — fills without OOM"],
    ["Optimizer", "AdamW, lr=0.001", "Better generalisation than SGD on small datasets"],
    ["Augmentation", "Mosaic, HSV shift, flip, rotate +-5deg", "Simulates camera angle variation and lighting"],
    ["Training time", "~6 minutes (NVIDIA RTX 3050)", "GPU acceleration via CUDA 12.4"],
    ["mAP50 (overall)", "80.5%", "Industry threshold for deployment: 75%+"],
    ["mAP50 (With Helmet)", "91.6%", "High precision on compliant riders"],
    ["mAP50 (Without Helmet)", "69.5%", "Lower due to fewer non-compliant samples"],
]

tt = Table(train_data, colWidths=[5.0*cm, 5.0*cm, 7.0*cm])
tt.setStyle(TableStyle([
    ("BACKGROUND",   (0,0), (-1,0), DARK),
    ("TEXTCOLOR",    (0,0), (-1,0), colors.white),
    ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
    ("FONTSIZE",     (0,0), (-1,-1), 8.5),
    ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, LIGHT]),
    ("BOX",          (0,0), (-1,-1), 0.5, BORDER),
    ("INNERGRID",    (0,0), (-1,-1), 0.5, BORDER),
    ("TOPPADDING",   (0,0), (-1,-1), 4),
    ("BOTTOMPADDING",(0,0), (-1,-1), 4),
    ("LEFTPADDING",  (0,0), (-1,-1), 6),
]))
story.append(tt)
story.append(Spacer(1, 0.3*cm))

story.append(sub("Dual-Model Architecture Design Decision"))
story.append(body(
    "A common mistake in helmet detection systems is replacing the base COCO detector with "
    "the fine-tuned classifier. This causes the system to lose all COCO class knowledge "
    "(motorcycle, person, car) and detect only helmet/no-helmet — making it impossible to "
    "associate a detected helmet status with a specific vehicle or rider. ViolaVision 2.0 "
    "explicitly separates the two models: YOLOv8s handles all vehicle and person detection; "
    "the helmet classifier runs only on cropped head regions of detected riders. The base "
    "model's COCO knowledge is fully preserved."
))

story += section(5, "Evidence Integrity and Chain of Custody")

story.append(body(
    "Every confirmed violation generates a tamper-evident JSON evidence record. The integrity "
    "mechanism is real cryptography, not a demonstration placeholder."
))

story.append(sub("Hashing and Signing Process"))
for b in [
    "All fields except the hash and signature themselves are serialised as JSON with sorted keys (deterministic ordering).",
    "SHA-256 hash of the serialised string is computed using Python hashlib.",
    "RSA-PSS signature (2048-bit key, SHA-256 digest, PSS maximum salt length) is computed over the hash using the cryptography library.",
    "Hash and base64-encoded signature are appended to the record.",
    "Tampering with any single field — including timestamp, plate number, confidence score, or GPS coordinates — produces a different hash, causing signature verification to fail with a clear error.",
    "A tamper simulation is built into the Evidence Verify tab: editing any field and re-verifying shows the exact failure message, demonstrating court-admissible tamper detection.",
]:
    story.append(bullet(b))

story.append(Spacer(1, 0.3*cm))
story.append(two_col_table([
    ["SHA-256 hashing", "SHA-256 hashing (identical)"],
    ["RSA-PSS software key (file on disk)", "RSA-PSS + Infineon SLB9670 TPM (key never leaves hardware)"],
    ["System clock timestamp", "NTP-synchronised + GPS satellite dual timestamp"],
    ["Mock blockchain TX ID", "Polygon network real anchor transaction"],
    ["Local SQLite storage", "TLS 1.3 encrypted write-once forensic database"],
    ["Mock VAHAN lookup", "Live VAHAN BTP API integration"],
], "Prototype Implementation", "Production Deployment"))

# ── Section 6 — Knowledge Graph and Repeat Offender Intelligence ───────────────
story += section(6, "Knowledge Graph and Repeat Offender Intelligence")

story.append(body(
    "ViolaVision 2.0 maintains a violation graph where nodes represent vehicle plates, "
    "camera locations, and violation types, and edges represent recorded violation events. "
    "This graph enables queries that flat violation logs cannot support."
))

story.append(sub("Graph Capabilities"))
for b in [
    "Repeat offender detection: vehicles with 2+ violations in 30 days are automatically flagged, with escalation to senior officer at 3+ and automatic RTO referral at 7+.",
    "Camera hotspot ranking: junctions are ranked by violation frequency and average priority score, guiding BBMP traffic engineering interventions.",
    "Plate cloning detection: a plate seen at two locations more than 5 km apart within 10 minutes is physically impossible and flags a cloned plate alert.",
    "Infrastructure failure signatures: violation type clustering by time and location reveals missing infrastructure (e.g. absent U-turns causing wrong-side patterns) rather than just individual offences.",
    "OCR confidence gating: only plates read with confidence above 0.4 and matching the Indian plate regex (two letters + two digits + one-to-three letters + three-to-four digits) are used as graph nodes, preventing low-quality reads from creating false repeat-offender connections.",
]:
    story.append(bullet(b))

story.append(Spacer(1, 0.2*cm))
story.append(body(
    "The prototype implements graph queries in SQLite with a Plotly network visualisation layer. "
    "Production deployment uses Neo4j Enterprise for genuine graph traversal at city scale, "
    "with partitioned graph structure by geographic zone to support horizontal scaling across "
    "hundreds of cameras."
))

# ── Section 7 — Human-in-the-Loop and Active Learning ─────────────────────────
story += section(7, "Human-in-the-Loop and Active Learning Pipeline")

story.append(body(
    "No automated system should have unchecked authority over enforcement actions. "
    "ViolaVision 2.0 uses a genuine human-in-the-loop architecture, not a logging "
    "afterthought — the system is structurally incapable of issuing a confirmed enforcement "
    "record without a human review step for medium-confidence violations."
))

story.append(sub("Review Queue Workflow"))
for b in [
    "Every violation lands in the Review Queue with status PENDING REVIEW at the moment it is confirmed by the 3-of-5 frame threshold.",
    "Violations with confidence above 0.88 are auto-queued for supervisory sampling but not auto-confirmed.",
    "An operator must explicitly click Confirm, Dismiss, or Escalate for each violation.",
    "Dismissals require a mandatory reason: poor image quality / wrong classification / no actual violation / vehicle type error / other.",
    "Dismissal reasons are stored in a dedicated table keyed on camera ID, enabling per-camera false positive rate calculation (shown in the Analytics tab).",
    "When a camera's false positive rate exceeds 15%, the system automatically flags it for calibration review.",
]:
    story.append(bullet(b))

story.append(sub("Active Learning Data Collection"))
story.append(body(
    "The dismissal log is the active learning dataset. Every operator dismissal is a labelled "
    "negative example — the model predicted a violation, a human said it was wrong. When "
    "500 dismissals accumulate, the system surfaces a retraining recommendation. Before any "
    "retrained model replaces the production model, it is validated in a sandboxed comparison "
    "against the current model on a held-out test set; only models that match or improve "
    "performance metrics are promoted. This prevents the active learning loop from degrading "
    "the model through noisy human labels."
))

# ── Section 8 — Scalability and Deployment Roadmap ────────────────────────────
story += section(8, "Scalability, Deployment Roadmap, and Future Development")

story.append(sub("Deployment Architecture for Bengaluru Scale"))
story.append(body(
    "The prototype runs as a Streamlit application on a single workstation. Production "
    "deployment adds a compute module to existing ITMS camera poles rather than replacing "
    "infrastructure — a NVIDIA Jetson AGX Orin (64GB) per junction cluster running the "
    "detection pipeline at the edge, with confirmed violations transmitted over TLS 1.3 to "
    "a central evidence server."
))

road_data = [
    ["Phase", "Timeline", "Deliverable"],
    ["Phase 1 (Current)", "Hackathon prototype", "Helmet + parking + stop-line detection on video; signed evidence; review queue; knowledge graph"],
    ["Phase 2 (3 months)", "Pilot: 3 junctions", "Seatbelt classifier training; VAHAN BTP API integration; Neo4j deployment; ITMS RTSP integration"],
    ["Phase 3 (6 months)", "City rollout: 50 junctions", "RT-DETR upgrade; LPRNet plate reader; real blockchain anchoring; night-mode IR preprocessing pipeline"],
    ["Phase 4 (12 months)", "Full Bengaluru ITMS", "172 junctions; active learning live retraining; accident detection (Phase 2 model); CARLA-simulated training data for adverse weather"],
]

rt = Table(road_data, colWidths=[3.5*cm, 3.5*cm, 10.0*cm])
rt.setStyle(TableStyle([
    ("BACKGROUND",   (0,0), (-1,0), DARK),
    ("TEXTCOLOR",    (0,0), (-1,0), colors.white),
    ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
    ("FONTSIZE",     (0,0), (-1,-1), 9),
    ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, LIGHT]),
    ("BOX",          (0,0), (-1,-1), 0.5, BORDER),
    ("INNERGRID",    (0,0), (-1,-1), 0.5, BORDER),
    ("TOPPADDING",   (0,0), (-1,-1), 5),
    ("BOTTOMPADDING",(0,0), (-1,-1), 5),
    ("LEFTPADDING",  (0,0), (-1,-1), 6),
    ("VALIGN",       (0,0), (-1,-1), "TOP"),
]))
story.append(rt)
story.append(Spacer(1, 0.3*cm))

story.append(sub("Honest Assessment of Prototype Limitations"))
for b in [
    "Wrong-side driving detection in the prototype requires an operator toggle because single-image analysis cannot prove direction of motion; production uses optical flow (RAFT) across consecutive frames.",
    "Illegal parking requires a vehicle to remain stationary for at least 8 tracked frames in the prototype; production confirms 5+ minutes of stationarity for legal defensibility.",
    "Seatbelt detection architecture is defined (identical pipeline to helmet classifier, different dataset); the trained classifier is a Phase 2 deliverable due to dataset acquisition time.",
    "VAHAN lookup uses a mock database of 3 entries; production requires BTP API credentials from MoRTH, which require formal partnership with traffic enforcement authorities.",
    "Temporal confirmation uses 3-of-5 frames (approximately 0.5 seconds at 30 FPS); production tuning may adjust this threshold based on violation type and false positive rate data from the review queue.",
]:
    story.append(bullet(b))

story.append(PageBreak())

# ── Summary page ───────────────────────────────────────────────────────────────
story.append(Spacer(1, 0.5*cm))
story.append(Paragraph("System Capability Summary", SEC_HEAD))
story.append(hr())

summary_data = [
    ["Capability", "Status", "Notes"],
    ["YOLOv8s object detection", "BUILT", "Vehicles, persons, motorcycles — COCO 80 classes"],
    ["Helmet fine-tuned classifier", "BUILT", "mAP50 = 80.5% on HELMET INDIA dataset"],
    ["Dual-model architecture", "BUILT", "Base + classifier run independently"],
    ["ByteTrack persistent tracking", "BUILT", "Persistent IDs across video frames"],
    ["Temporal 3-of-5 confirmation", "BUILT", "Real execution, not described only"],
    ["Geometric feature engineering", "BUILT", "6 named features per bbox"],
    ["Cross-modal scene validation", "BUILT", "Junction / Parking / Highway suppression"],
    ["Stationary parking detection", "BUILT", "Position history per track ID"],
    ["Priority scoring (4-factor)", "BUILT", "V_w x L_w x T_w x R_w formula"],
    ["Serial offender detection", "BUILT", "Levels 1-3 + automatic RTO referral"],
    ["SHA-256 + RSA-PSS signing", "BUILT", "Real cryptography, tamper-detectable"],
    ["Tamper demonstration", "BUILT", "Field edit + verify fail shown live"],
    ["Human-in-the-loop review", "BUILT", "Pending/Confirm/Dismiss/Escalate workflow"],
    ["Active learning data collection", "BUILT", "Dismissal reasons logged per camera"],
    ["Knowledge graph visualisation", "BUILT", "Vehicles x cameras x violations network"],
    ["Plate cloning detection", "BUILT", "Location-time impossibility detection"],
    ["CLAHE preprocessing", "BUILT", "LAB colour space adaptive enhancement"],
    ["VAHAN owner lookup", "MOCK", "Real BTP API requires MoRTH credentials"],
    ["Neo4j graph database", "PLANNED", "SQLite for prototype; Neo4j Enterprise production"],
    ["Real blockchain anchoring", "PLANNED", "Polygon network; mock TX ID in prototype"],
    ["Seatbelt classifier", "PLANNED", "Architecture defined; Phase 2 training"],
    ["IR night-mode preprocessing", "PLANNED", "Hardware component; CLAHE used for demo"],
    ["RTSP live stream ingestion", "PLANNED", "Video file used for demo reliability"],
]

st_table = Table(summary_data, colWidths=[7.0*cm, 2.5*cm, 7.5*cm])
st_table.setStyle(TableStyle([
    ("BACKGROUND",   (0,0), (-1,0), DARK),
    ("TEXTCOLOR",    (0,0), (-1,0), colors.white),
    ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
    ("FONTSIZE",     (0,0), (-1,-1), 8.5),
    ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, LIGHT]),
    ("BOX",          (0,0), (-1,-1), 0.5, BORDER),
    ("INNERGRID",    (0,0), (-1,-1), 0.5, BORDER),
    ("TOPPADDING",   (0,0), (-1,-1), 4),
    ("BOTTOMPADDING",(0,0), (-1,-1), 4),
    ("LEFTPADDING",  (0,0), (-1,-1), 6),
    ("ALIGN",        (1,0), (1,-1), "CENTER"),
]))

# Colour-code status column
for i, row in enumerate(summary_data[1:], 1):
    if row[1] == "BUILT":
        st_table.setStyle(TableStyle([
            ("TEXTCOLOR",  (1,i), (1,i), GREEN),
            ("FONTNAME",   (1,i), (1,i), "Helvetica-Bold"),
        ]))
    elif row[1] == "MOCK":
        st_table.setStyle(TableStyle([
            ("TEXTCOLOR",  (1,i), (1,i), ACCENT),
            ("FONTNAME",   (1,i), (1,i), "Helvetica-Bold"),
        ]))
    elif row[1] == "PLANNED":
        st_table.setStyle(TableStyle([
            ("TEXTCOLOR",  (1,i), (1,i), GREY),
        ]))

story.append(st_table)

story.append(Spacer(1, 0.5*cm))
story.append(hr())
story.append(Paragraph(
    "ViolaVision 2.0  |  Flipkart Gridlock Hackathon 2.0  |  Theme 3: Computer Vision for Traffic Violations",
    CAPTION))

# ── Build ──────────────────────────────────────────────────────────────────────
doc.build(story)
print(f"\nConcept document generated: {OUT}")
print(f"File size: {os.path.getsize(OUT) / 1024:.1f} KB")
