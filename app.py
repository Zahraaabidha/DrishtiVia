import streamlit as st
import cv2
import numpy as np
from PIL import Image
import hashlib
import json
import time
import base64
import sqlite3
import re
import os
import tempfile
from collections import defaultdict, deque
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from ultralytics import YOLO
import easyocr

# Optional Neo4j — graceful fallback to SQLite if not installed / not running
try:
    from neo4j import GraphDatabase as _Neo4jDriver
    _NEO4J_AVAILABLE = True
except ImportError:
    _NEO4J_AVAILABLE = False

# ── page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ViolaVision 2.0",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global UI — Elysium bento skin (single protected <style> block) ───────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@300;400;500;600;700;800&display=swap');

/* ═══════════════════════════════════════════════════════════════
   RESET + BASE
   ═══════════════════════════════════════════════════════════════ */
*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] {
    font-family: 'Inter', ui-sans-serif, system-ui, sans-serif;
    color: #111111;
    -webkit-font-smoothing: antialiased;
    letter-spacing: -0.01em;
}

/* ═══════════════════════════════════════════════════════════════
   LAYOUT CANVAS  — off-white (#F8F9FA) to make white tiles pop
   ═══════════════════════════════════════════════════════════════ */
.stApp { background: #F8F9FA !important; }
#MainMenu, header[data-testid="stHeader"], footer { visibility: hidden !important; height: 0 !important; overflow: hidden !important; }
.block-container { padding: 0.6rem 1.8rem 2rem 1.8rem !important; max-width: 100% !important; }

/* ═══════════════════════════════════════════════════════════════
   SIDEBAR — white card, full height, clean
   ═══════════════════════════════════════════════════════════════ */
section[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid rgba(0,0,0,0.05) !important;
}
section[data-testid="stSidebar"] > div:first-child { padding: 0.8rem 1rem 1.4rem 1rem !important; }
section[data-testid="stSidebar"] .stMarkdown p { font-size: 0.75rem; color: rgba(0,0,0,0.5); }
section[data-testid="stSidebar"] .stMarkdown strong { color: rgba(0,0,0,0.25); font-size: 0.6rem; letter-spacing: 0.14em; text-transform: uppercase; }
section[data-testid="stSidebar"] label { font-size: 0.72rem !important; color: rgba(0,0,0,0.5) !important; font-weight: 500 !important; }
section[data-testid="stSidebar"] hr { border-color: rgba(0,0,0,0.05) !important; margin: 0.7rem 0 !important; }
section[data-testid="stSidebar"] [data-testid="metric-container"] {
    background: #F8F9FA !important; border: none !important; box-shadow: none !important; padding: 0.4rem 0 !important;
}
section[data-testid="stSidebar"] [data-testid="metric-container"] [data-testid="stMetricValue"] { font-size: 1.3rem !important; }

/* ═══════════════════════════════════════════════════════════════
   BENTO TILES  — every st.container(border=True) becomes a card
   ═══════════════════════════════════════════════════════════════ */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #ffffff !important;
    border: 1px solid rgba(0,0,0,0.06) !important;
    border-radius: 28px !important;
    box-shadow: 0 2px 4px rgba(0,0,0,0.02), 0 12px 32px -16px rgba(0,0,0,0.07) !important;
    transition: box-shadow 0.22s ease, transform 0.22s ease !important;
    overflow: hidden !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    box-shadow: 0 2px 4px rgba(0,0,0,0.02), 0 20px 40px -14px rgba(0,0,0,0.11) !important;
    transform: translateY(-2px) !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"] {
    padding: 1.3rem 1.4rem !important;
}

/* ═══════════════════════════════════════════════════════════════
   TABS — segmented pill nav (black active chip, like Elysium)
   ═══════════════════════════════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px !important;
    background: #ffffff !important;
    border: 1px solid rgba(0,0,0,0.05) !important;
    border-radius: 18px !important;
    padding: 5px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03) !important;
    margin-bottom: 1.2rem !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 14px !important;
    padding: 0.5rem 1.1rem !important;
    font-size: 0.7rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.05em !important;
    text-transform: uppercase !important;
    color: rgba(0,0,0,0.4) !important;
    border-bottom: none !important;
    background: transparent !important;
    transition: all 0.15s ease !important;
}
.stTabs [aria-selected="true"] {
    color: #ffffff !important;
    background: #111111 !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.14) !important;
}
.stTabs [data-baseweb="tab"]:hover:not([aria-selected="true"]) { color: rgba(0,0,0,0.7) !important; background: rgba(0,0,0,0.04) !important; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none !important; }
.stTabs [data-baseweb="tab-panel"] { padding: 0.6rem 0 0 0 !important; }

/* ═══════════════════════════════════════════════════════════════
   METRIC CARDS  — stat tiles with big Outfit number
   ═══════════════════════════════════════════════════════════════ */
[data-testid="metric-container"] {
    background: #ffffff !important;
    border: 1px solid rgba(0,0,0,0.05) !important;
    border-radius: 24px !important;
    padding: 1.3rem 1.4rem !important;
    box-shadow: 0 2px 4px rgba(0,0,0,0.02), 0 10px 28px -14px rgba(0,0,0,0.07) !important;
    transition: box-shadow 0.2s ease, transform 0.2s ease !important;
}
[data-testid="metric-container"]:hover {
    box-shadow: 0 2px 4px rgba(0,0,0,0.02), 0 18px 36px -12px rgba(0,0,0,0.11) !important;
    transform: translateY(-2px) !important;
}
[data-testid="metric-container"] label {
    font-size: 0.6rem !important; font-weight: 700 !important;
    letter-spacing: 0.14em !important; text-transform: uppercase !important;
    color: rgba(0,0,0,0.25) !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-family: 'Outfit', sans-serif !important;
    font-size: 2.1rem !important; font-weight: 600 !important;
    color: #111111 !important; letter-spacing: -0.04em !important;
}
[data-testid="metric-container"] [data-testid="stMetricDelta"] { font-size: 0.72rem !important; }

/* ═══════════════════════════════════════════════════════════════
   BUTTONS — black pill primary / white outline secondary
   ═══════════════════════════════════════════════════════════════ */
.stButton > button {
    border-radius: 9999px !important;
    font-size: 0.7rem !important; font-weight: 700 !important;
    letter-spacing: 0.08em !important; text-transform: uppercase !important;
    padding: 0.6rem 1.5rem !important;
    border: 1px solid rgba(0,0,0,0.08) !important;
    transition: all 0.18s ease !important;
}
.stButton > button[kind="primary"] {
    background: #111111 !important; border-color: #111111 !important; color: #fff !important;
    box-shadow: 0 4px 14px rgba(0,0,0,0.1) !important;
}
.stButton > button[kind="primary"]:hover {
    background: #2a2a2a !important; border-color: #2a2a2a !important;
    box-shadow: 0 6px 18px rgba(0,0,0,0.15) !important; transform: translateY(-1px) !important;
}
.stButton > button:not([kind="primary"]) { background: #fff !important; color: #111 !important; }
.stButton > button:not([kind="primary"]):hover {
    background: #f3f4f6 !important; transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05) !important;
}

/* ═══════════════════════════════════════════════════════════════
   EXPANDERS  — bento violation cards
   ═══════════════════════════════════════════════════════════════ */
[data-testid="stExpander"] {
    background: #ffffff !important; border: 1px solid rgba(0,0,0,0.05) !important;
    border-radius: 22px !important; overflow: hidden !important; margin-bottom: 10px !important;
    box-shadow: 0 2px 4px rgba(0,0,0,0.02), 0 8px 24px -16px rgba(0,0,0,0.07) !important;
    transition: box-shadow 0.2s ease !important;
}
[data-testid="stExpander"]:hover { box-shadow: 0 2px 4px rgba(0,0,0,0.02), 0 16px 32px -12px rgba(0,0,0,0.1) !important; }
[data-testid="stExpander"] summary { font-size: 0.82rem !important; font-weight: 600 !important; color: #111 !important; padding: 0.9rem 1.1rem !important; }
[data-testid="stExpander"] summary:hover { background: rgba(0,0,0,0.015) !important; }

/* ═══════════════════════════════════════════════════════════════
   INPUTS / SELECTS / SLIDERS / TOGGLES
   ═══════════════════════════════════════════════════════════════ */
.stTextInput input, [data-testid="stTextInput"] input {
    background: #F8F9FA !important; border: 1px solid rgba(0,0,0,0.07) !important;
    border-radius: 12px !important; color: #111 !important; font-size: 0.82rem !important;
}
.stTextInput input:focus { border-color: #111 !important; box-shadow: 0 0 0 3px rgba(17,17,17,0.06) !important; }
[data-testid="stSelectbox"] > div > div {
    background: #F8F9FA !important; border: 1px solid rgba(0,0,0,0.07) !important;
    border-radius: 12px !important; font-size: 0.82rem !important;
}
div[data-testid="stSlider"] [role="slider"] { background: #111 !important; border-color: #111 !important; }
div[data-testid="stSlider"] [data-baseweb="slider"] > div > div { background: #111 !important; }
div[data-testid="stSlider"] [data-baseweb="slider"] > div { background: rgba(0,0,0,0.08) !important; }
[data-baseweb="checkbox"] div[role="switch"][aria-checked="true"] { background: #111 !important; }

/* ═══════════════════════════════════════════════════════════════
   DATAFRAME
   ═══════════════════════════════════════════════════════════════ */
[data-testid="stDataFrame"] {
    border: 1px solid rgba(0,0,0,0.05) !important; border-radius: 18px !important;
    overflow: hidden !important; box-shadow: 0 2px 4px rgba(0,0,0,0.02) !important;
}
.stDataFrame thead th {
    background: #fafafa !important; font-size: 0.62rem !important; font-weight: 700 !important;
    letter-spacing: 0.1em !important; text-transform: uppercase !important;
    color: rgba(0,0,0,0.35) !important; border-bottom: 1px solid rgba(0,0,0,0.04) !important;
    padding: 0.8rem 1rem !important;
}
.stDataFrame tbody tr:hover { background: rgba(0,0,0,0.015) !important; }
.stDataFrame tbody td { border-bottom: 1px solid rgba(0,0,0,0.03) !important; font-size: 0.8rem !important; padding: 0.65rem 1rem !important; }

/* ═══════════════════════════════════════════════════════════════
   MISC
   ═══════════════════════════════════════════════════════════════ */
[data-testid="stAlert"] { border-radius: 16px !important; border: 1px solid rgba(0,0,0,0.05) !important; }
[data-testid="stImage"] img { border-radius: 18px !important; border: 1px solid rgba(0,0,0,0.05) !important; }
hr { border: none !important; border-top: 1px solid rgba(0,0,0,0.05) !important; margin: 0.8rem 0 !important; }
.stCaption, [data-testid="stCaptionContainer"] { color: rgba(0,0,0,0.38) !important; font-size: 0.7rem !important; }
[data-testid="stProgressBar"] > div { background: rgba(0,0,0,0.05) !important; border-radius: 4px !important; }
[data-testid="stProgressBar"] > div > div { background: #111 !important; border-radius: 4px !important; }
.js-plotly-plot .plotly, .js-plotly-plot .plotly .bg { fill: transparent !important; }

/* ═══════════════════════════════════════════════════════════════
   TYPOGRAPHY
   ═══════════════════════════════════════════════════════════════ */
h1 { font-family: 'Outfit', sans-serif !important; font-size: 2rem !important; font-weight: 700 !important; letter-spacing: -0.03em !important; color: #111 !important; }
h2 { font-size: 0.6rem !important; font-weight: 700 !important; letter-spacing: 0.16em !important; text-transform: uppercase !important; color: rgba(0,0,0,0.25) !important; margin: 0.8rem 0 0.3rem !important; }
h3 { font-size: 0.9rem !important; font-weight: 600 !important; color: #111 !important; }

/* ═══════════════════════════════════════════════════════════════
   SHELL COMPONENTS  (top bar, sidebar logo, promo card)
   ═══════════════════════════════════════════════════════════════ */
#MainMenu, header[data-testid="stHeader"], footer { visibility: hidden !important; height: 0 !important; }

.vv-topbar {
    display: flex; align-items: center; justify-content: space-between;
    background: #ffffff; border: 1px solid rgba(0,0,0,0.05);
    border-radius: 28px; padding: 0.65rem 1.3rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.02), 0 8px 24px -16px rgba(0,0,0,0.06);
    margin-bottom: 1.4rem;
}
.vv-search {
    display: flex; align-items: center; gap: 10px; width: 300px;
    background: #F8F9FA; border-radius: 9999px; padding: 0.55rem 1rem;
    color: rgba(0,0,0,0.35); font-size: 0.78rem; font-weight: 500; border: 1px solid rgba(0,0,0,0.04);
}
.vv-search .kbd {
    margin-left: auto; font-size: 0.6rem; font-weight: 700;
    color: rgba(0,0,0,0.3); background: #fff; border: 1px solid rgba(0,0,0,0.08);
    border-radius: 5px; padding: 1px 5px;
}
.vv-right-shell { display: flex; align-items: center; gap: 12px; }
.vv-icon-btn {
    width: 38px; height: 38px; display: inline-flex; align-items: center; justify-content: center;
    border-radius: 50% !important; border: 1px solid rgba(0,0,0,0.06); background: #fff;
    color: rgba(0,0,0,0.4); cursor: pointer; transition: all 0.18s ease;
}
.vv-icon-btn:hover { background: #F8F9FA; color: #111; }
.vv-user { display: flex; align-items: center; gap: 10px; padding-left: 12px; border-left: 1px solid rgba(0,0,0,0.07); }
.vv-user .meta { text-align: right; line-height: 1.25; }
.vv-user .name { font-size: 0.78rem; font-weight: 700; color: #111; }
.vv-user .role { font-size: 0.62rem; color: rgba(0,0,0,0.38); }
.vv-avatar {
    width: 38px; height: 38px; border-radius: 50% !important;
    background: #111; display: inline-flex; align-items: center; justify-content: center;
    color: #fff; font-weight: 700; font-size: 0.78rem; font-family: 'Outfit', sans-serif;
    border: 2px solid #fff; box-shadow: 0 2px 6px rgba(0,0,0,0.1);
}
.vv-logo {
    display: flex; align-items: center; gap: 10px; padding: 0.4rem 0 0.6rem 0;
}
.vv-logo .mark {
    width: 34px; height: 34px; border-radius: 9px; background: #111;
    display: inline-flex; align-items: center; justify-content: center;
}
.vv-logo .mark::after {
    content: ""; width: 13px; height: 13px; border-radius: 50%; border: 2.5px solid #fff;
}
.vv-logo .word {
    font-family: 'Outfit', sans-serif; font-size: 1.1rem; font-weight: 800;
    letter-spacing: -0.02em; color: #111; text-transform: uppercase;
}
.vv-menu-label {
    font-size: 0.56rem; font-weight: 700; letter-spacing: 0.18em;
    text-transform: uppercase; color: rgba(0,0,0,0.25); margin: 1.1rem 0 0.35rem 2px;
}
.vv-promo {
    background: #111111; border-radius: 24px; padding: 1.2rem 1.1rem; margin-top: 0.8rem;
    color: #fff; position: relative; overflow: hidden;
}
.vv-promo .pic { font-size: 1.5rem; margin-bottom: 0.5rem; }
.vv-promo .h { font-family: 'Outfit',sans-serif; font-size: 0.9rem; font-weight: 700; color: #fff; margin-bottom: 0.3rem; }
.vv-promo .s { font-size: 0.65rem; color: rgba(255,255,255,0.4); line-height: 1.4; margin-bottom: 0.7rem; }
.vv-promo .stat { display:flex; align-items:center; gap:6px; font-size:0.65rem; color:rgba(255,255,255,0.5); }
.vv-promo .dot { width:6px; height:6px; border-radius:50%; background:#22c55e; flex-shrink:0; }
</style>
""", unsafe_allow_html=True)

# ── Top bar (Elysium shell) ───────────────────────────────────────────────────
st.markdown("""
<div class="vv-topbar">
  <!-- Search left -->
  <div class="vv-search">
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-search"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
    <span>Search plate, location, violation…</span>
    <span class="kbd">⌘F</span>
  </div>
  
  <!-- Tools & Profile right -->
  <div class="vv-right-shell">
    <div class="vv-icon-btn">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-info"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
    </div>
    <div class="vv-icon-btn">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-mail"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>
    </div>
    <div class="vv-icon-btn" style="position: relative;">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-bell"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>
      <span style="position: absolute; top: 11px; right: 11px; width: 6px; height: 6px; border-radius: 50%; background: #ef4444; border: 1.5px solid #ffffff;"></span>
    </div>
    <div class="vv-user">
      <div class="meta">
        <div class="name">Traffic Operator</div>
        <div class="role">Bengaluru Control Room</div>
      </div>
      <div class="vv-avatar">TO</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── paths ─────────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(BASE_DIR, "evidence_store", "violations.db")
KEY_PATH   = os.path.join(BASE_DIR, "models", "signing_key.pem")

# ── load / generate signing key ───────────────────────────────────────────────
@st.cache_resource
def get_signing_key():
    if os.path.exists(KEY_PATH):
        with open(KEY_PATH, "rb") as f:
            private_key = serialization.load_pem_private_key(
                f.read(), password=None, backend=default_backend())
    else:
        private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048,
            backend=default_backend())
        with open(KEY_PATH, "wb") as f:
            f.write(private_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption()))
    return private_key

# ── load YOLO ─────────────────────────────────────────────────────────────────
HELMET_MODEL_PATH = os.path.join(
    BASE_DIR,
    "runs", "detect", "runs", "helmet_train", "violavision_v1", "weights", "best.pt"
)
SEATBELT_MODEL_PATH = os.path.join(
    BASE_DIR,
    "runs", "detect", "runs", "seatbelt_train",
    "violavision_seatbelt_v1-2", "weights", "best.pt"
)
WRONGSIDE_MODEL_PATH = os.path.join(
    BASE_DIR,
    "runs", "detect", "runs", "wrongside_train",
    "violavision_wrongside_v1", "weights", "best.pt"
)

@st.cache_resource
def get_yolo():
    """Base COCO model — always loaded for vehicle/person/motorcycle detection."""
    return YOLO("yolov8s.pt")

@st.cache_resource
def get_helmet_yolo():
    """Fine-tuned helmet classifier — runs on person head crops."""
    if os.path.exists(HELMET_MODEL_PATH):
        return YOLO(HELMET_MODEL_PATH)
    return None

@st.cache_resource
def get_seatbelt_yolo():
    """Fine-tuned seatbelt classifier — runs on car interior crops."""
    if os.path.exists(SEATBELT_MODEL_PATH):
        return YOLO(SEATBELT_MODEL_PATH)
    return None

@st.cache_resource
def get_wrongside_yolo():
    """Fine-tuned wrong-side driving detector — runs on full-frame vehicle crops."""
    if os.path.exists(WRONGSIDE_MODEL_PATH):
        return YOLO(WRONGSIDE_MODEL_PATH)
    return None

@st.cache_resource
def get_rtdetr():
    """
    RT-DETR second-stage verifier (loaded lazily, only if the toggle is on).
    Used to confirm that a flagged crop genuinely contains the relevant object
    (person / motorcycle / car) before the violation is logged — a cheap way to
    weed out YOLO false positives. Runs only on confirmed crops, so the cost is
    bounded even on a 4GB GPU. Falls back to None if the weights can't load.
    """
    try:
        from ultralytics import RTDETR
        return RTDETR("rtdetr-l.pt")   # auto-downloads ~63MB on first use
    except Exception as e:
        st.warning(f"RT-DETR could not load ({e}). Continuing without verifier.")
        return None

# COCO class ids RT-DETR should expect inside a crop, per violation type
_RTDETR_EXPECT = {
    "Helmet Non-Compliance": {0, 3},      # person, motorcycle
    "Triple Riding":         {0, 3},
    "Illegal Parking":       {2, 5, 7},   # car, bus, truck
    "Stop-Line Violation":   {2, 3, 5, 7},
    "Red-Light Violation":   {2, 3, 5, 7},
    "Wrong-Side Driving":    {2, 3, 5, 7},
}

def rtdetr_confirms(crop: np.ndarray, vio_type: str, rtdetr_model) -> bool:
    """
    True if RT-DETR finds at least one expected object class in the crop.
    If the model is unavailable or the crop is too small, defaults to True
    (fail-open — never block a real violation because the verifier is absent).
    """
    if rtdetr_model is None or crop is None or crop.size == 0:
        return True
    if crop.shape[0] < 16 or crop.shape[1] < 16:
        return True
    expected = _RTDETR_EXPECT.get(vio_type)
    if not expected:
        return True
    try:
        res = rtdetr_model(crop, verbose=False, conf=0.35)
        found = {int(b.cls) for b in res[0].boxes}
        return bool(found & expected)
    except Exception:
        return True

def classify_helmet(person_bbox, frame_bgr, helmet_model):
    """
    Run the fine-tuned helmet model on the rider's head region.

    On low-resolution footage a rider may be only ~50px tall, so the head crop
    is tiny and the model returns nothing. We UPSCALE small crops to a usable
    size before classification, which roughly doubles the hit rate (verified on
    demo_helmet.mp4: 358x640 source). conf=0.15 lets weak-but-real detections
    through; the caller decides HIGH vs MEDIUM (review) from the returned value.

    Returns (class_name, confidence) or (None, 0.0) if inconclusive.
    """
    x1, y1, x2, y2 = [int(c) for c in person_bbox]
    h = y2 - y1
    # Head + shoulders: top 45% gives the model helmet context without the body
    head_y2 = y1 + max(int(h * 0.45), 20)
    crop = frame_bgr[max(0, y1):head_y2, max(0, x1):x2]
    if crop.size == 0 or crop.shape[0] < 8 or crop.shape[1] < 8:
        return None, 0.0
    # Upscale small crops so the 640px-trained model has enough detail
    if min(crop.shape[:2]) < 80:
        scale = max(2, int(96 / max(min(crop.shape[:2]), 1)))
        crop = cv2.resize(crop, None, fx=scale, fy=scale,
                          interpolation=cv2.INTER_CUBIC)
    results = helmet_model(crop, conf=0.15, verbose=False)
    boxes = results[0].boxes
    if not boxes:
        return None, 0.0
    names = results[0].names
    best = max(boxes, key=lambda b: float(b.conf))
    return names[int(best.cls)], float(best.conf)

# ── load EasyOCR ──────────────────────────────────────────────────────────────
@st.cache_resource
def get_ocr():
    return easyocr.Reader(["en"], gpu=False)

# ── database ──────────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS violations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            plate_number TEXT,
            violation_type TEXT,
            confidence REAL,
            priority_score REAL,
            priority_level TEXT,
            evidence_hash TEXT,
            camera_id TEXT,
            operator_action TEXT,
            operator_timestamp REAL,
            dismissal_reason TEXT
        )""")
    # Migration: add snapshot_path to existing DBs that predate this column
    try:
        conn.execute("ALTER TABLE violations ADD COLUMN snapshot_path TEXT")
    except sqlite3.OperationalError:
        pass   # column already exists
    # seed repeat-offender sample rows
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM violations")
    if cur.fetchone()[0] == 0:
        seed = [
            (time.time()-86400, "KA01AB1234", "Helmet Non-Compliance",
             0.91, 9.8, "HIGH", "abc123", "silk_board", None, None, None),
            (time.time()-72000, "KA01AB1234", "Triple Riding",
             0.89, 13.2, "HIGH", "def456", "silk_board", None, None, None),
            (time.time()-50000, "KA01AB1234", "Red-Light Violation",
             0.94, 18.6, "CRITICAL", "ghi789", "kr_circle", None, None, None),
            (time.time()-3600,  "MH02XY9999", "Helmet Non-Compliance",
             0.87, 8.4, "MEDIUM", "jkl012", "hebbal", None, None, None),
        ]
        conn.executemany("""
            INSERT INTO violations
            (timestamp,plate_number,violation_type,confidence,
             priority_score,priority_level,evidence_hash,camera_id,
             operator_action,operator_timestamp,dismissal_reason)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)""", seed)
    conn.commit()
    return conn

# ── preprocessing ─────────────────────────────────────────────────────────────
def preprocess(frame: np.ndarray, enable: bool = True) -> np.ndarray:
    if not enable:
        return frame
    # CLAHE for contrast / low-light / shadow recovery
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    frame = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)
    # Dark-channel dehaze — recovers detail behind atmospheric scattering / rain
    dark = np.min(frame, axis=2).astype(np.float32)
    atm  = float(np.percentile(dark, 95)) + 1e-6
    t    = np.clip(1.0 - 0.75 * dark / atm, 0.3, 1.0)
    out  = frame.astype(np.float32)
    for c in range(3):
        out[:, :, c] = np.clip((out[:, :, c] - atm) / t + atm, 0, 255)
    return out.astype(np.uint8)

# ── violation detection ───────────────────────────────────────────────────────
def bbox_iou_overlap(b1, b2):
    """Check if two bboxes overlap significantly."""
    ix1 = max(b1[0], b2[0]); iy1 = max(b1[1], b2[1])
    ix2 = min(b1[2], b2[2]); iy2 = min(b1[3], b2[3])
    if ix2 < ix1 or iy2 < iy1:
        return 0.0
    inter = (ix2-ix1)*(iy2-iy1)
    area1 = (b1[2]-b1[0])*(b1[3]-b1[1])
    return inter / (area1 + 1e-6)

def person_on_motorcycle(person_bbox, bike_bbox, tolerance=80):
    """
    True if person is riding the motorcycle.
    Requires BOTH positional proximity AND meaningful bbox overlap.
    Overlap requirement prevents background pedestrians from being counted.
    """
    px_c = (person_bbox[0]+person_bbox[2])/2
    bx_c = (bike_bbox[0]+bike_bbox[2])/2
    bw   = bike_bbox[2] - bike_bbox[0]
    # Person centre must be within the bike's horizontal span + tolerance
    horizontal_ok = abs(px_c - bx_c) < bw / 2 + tolerance
    # Must share actual pixel area with the motorcycle bbox
    overlap = bbox_iou_overlap(person_bbox, bike_bbox)
    overlap_ok = overlap > 0.08   # raised from 0.05 — background persons have near-zero overlap
    return horizontal_ok and overlap_ok

def extract_geometric_features(bbox, img_shape):
    """
    Explicit bounding-box geometric feature engineering.
    Returns a dict of named features used downstream in violation logic.
    """
    x1, y1, x2, y2 = bbox
    img_h, img_w = img_shape[:2]
    w = x2 - x1
    h = y2 - y1
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    return {
        "aspect_ratio":      round(w / (h + 1e-6), 3),   # w/h > 1.5 = wide (vehicle from front)
        "norm_x":            round(cx / img_w, 3),         # 0=left, 1=right of frame
        "norm_y":            round(cy / img_h, 3),         # 0=top, 1=bottom of frame
        "norm_area":         round((w * h) / (img_w * img_h), 4),  # fraction of frame area
        "bottom_frac":       round(y2 / img_h, 3),         # how far down the object reaches
        "is_riding_posture": (0.3 < (h / (w + 1e-6)) < 2.5),      # person not lying flat
    }

def detect_violations(results, stop_line_y: int = 400, img_shape=(720, 1280),
                      frame_bgr=None, helmet_model=None, track_ids=None,
                      seatbelt_model=None, wrongside_model=None):
    """
    Dual-model violation detection pipeline.
    - Base COCO model (yolov8s): detects vehicles, persons, motorcycles
    - Fine-tuned helmet model: classifies person crops into With/Without Helmet
    - Geometric features extracted per bbox for downstream violation logic
    """
    names = results[0].names
    boxes = results[0].boxes

    # Read track IDs aligned 1:1 with boxes. ByteTrack (persist=True) assigns a
    # stable id per physical object across frames. We carry this id through the
    # conf filter so each violation can be tied to the SAME object every frame —
    # this is what makes 3-of-5 temporal confirmation actually accumulate.
    box_ids = (boxes.id.int().tolist()
               if getattr(boxes, "id", None) is not None
               else [None] * len(boxes))

    # dets: list of (bbox, cls_name, conf, track_id)
    dets = []
    for j, box in enumerate(boxes):
        cls_name = names[int(box.cls)]
        conf     = float(box.conf)
        if conf < 0.35:
            continue
        tid = box_ids[j] if j < len(box_ids) else None
        dets.append((box.xyxy[0].tolist(), cls_name, conf, tid))

    motorcycles  = [(b, c, t) for b, cls, c, t in dets if cls == "motorcycle"]
    persons      = [(b, c, t) for b, cls, c, t in dets if cls == "person"]
    vehicles     = [(b, c, t) for b, cls, c, t in dets
                    if cls in {"motorcycle", "car", "truck", "bus", "bicycle"}]
    # Only cars eligible for illegal parking — buses/trucks stop at bus stops/junctions legally
    parked_types = [(b, c, t) for b, cls, c, t in dets if cls == "car"]

    # Debug capture — raw helmet model outputs, surfaced in the Debug panel
    helmet_debug = []

    violations = []
    signal_red   = st.session_state.get("signal_red", False)
    scene_type   = st.session_state.get("scene_type", "Junction")
    wrong_side   = st.session_state.get("wrong_side_present", False)
    flow_dir     = st.session_state.get("flow_direction", "Left → Right")

    # ── 1. Helmet Non-Compliance (dual-model) ─────────────────────────────────
    # For each person on a motorcycle:
    #   a) If fine-tuned model available: classify the head crop
    #   b) Fallback: flag for human review (helmet status unknown)
    for bike_bbox, bike_conf, bike_tid in motorcycles:
        riders = [(p, pc) for p, pc, pt in persons
                  if person_on_motorcycle(p, bike_bbox)]
        if not riders:
            continue
        for person_bbox, person_conf in riders:
            geo = extract_geometric_features(person_bbox, img_shape)
            if helmet_model is not None and frame_bgr is not None:
                cls_name, helm_conf = classify_helmet(
                    person_bbox, frame_bgr, helmet_model)
                helmet_debug.append({
                    "track_id": bike_tid,
                    "class":    cls_name or "no-output",
                    "conf":     round(helm_conf, 2),
                })
                if cls_name and "with" in cls_name.lower() and helm_conf >= 0.38:
                    pass   # clearly helmeted — skip
                elif cls_name and "without" in cls_name.lower() and helm_conf >= 0.45:
                    # Confident no-helmet — HIGH, auto-flag
                    violations.append({
                        "type":        "Helmet Non-Compliance",
                        "confidence":  round(helm_conf, 2),
                        "bbox":        person_bbox,
                        "track_id":    bike_tid,
                        "severity":    "HIGH",
                        "description": f"Fine-tuned model: WITHOUT helmet (conf {helm_conf:.0%}). "
                                       f"Riding posture: {geo['is_riding_posture']}",
                        "geo_features": geo,
                    })
                elif cls_name and "without" in cls_name.lower() and helm_conf >= 0.20:
                    # Medium confidence no-helmet — route to human review
                    violations.append({
                        "type":        "Helmet Non-Compliance",
                        "confidence":  round(helm_conf, 2),
                        "bbox":        person_bbox,
                        "track_id":    bike_tid,
                        "severity":    "MEDIUM",
                        "description": f"Helmet status uncertain (conf {helm_conf:.0%}) — "
                                       f"human review required before any enforcement.",
                        "geo_features": geo,
                    })
                # cls_name is None or very weak signal → skip (too noisy to act on)
            else:
                # No fine-tuned model — fallback heuristic
                violations.append({
                    "type":        "Helmet Non-Compliance",
                    "confidence":  round(min(bike_conf + 0.05, 0.72), 2),
                    "bbox":        bike_bbox,
                    "track_id":    bike_tid,
                    "severity":    "MEDIUM",
                    "description": "Rider on motorcycle — helmet unverifiable (base model only).",
                    "geo_features": geo,
                })

    # ── 2. Triple Riding ──────────────────────────────────────────────────────
    # Strict overlap + riding posture check to reduce false positives in
    # dense traffic where unrelated pedestrians stand near parked bikes.
    for bike_bbox, bike_conf, bike_tid in motorcycles:
        bw = bike_bbox[2] - bike_bbox[0]
        tight_tol = max(int(bw * 0.4), 25)
        riding_persons = []
        for p, _, _ in persons:
            geo = extract_geometric_features(p, img_shape)
            if (person_on_motorcycle(p, bike_bbox, tolerance=tight_tol)
                    and geo["is_riding_posture"]):   # posture filter
                riding_persons.append(p)
        if len(riding_persons) >= 3:
            violations.append({
                "type":        "Triple Riding",
                "confidence":  round(min(bike_conf + 0.05, 0.88), 2),
                "bbox":        bike_bbox,
                "track_id":    bike_tid,
                "severity":    "HIGH",
                "description": (f"{len(riding_persons)} riders with motorcycle posture on "
                                f"one bike. NOTE: production uses temporal tracking to confirm."),
            })

    # ── 2b. Seatbelt Non-Compliance ───────────────────────────────────────────
    # Run fine-tuned seatbelt model on each car crop. Only acts on
    # 'person-noseatbelt'; 'person-seatbelt' clears the car silently.
    if seatbelt_model is not None and frame_bgr is not None:
        cars = [(b, c, t) for b, cls, c, t in dets if cls == "car"]
        for car_bbox, car_conf, car_tid in cars:
            x1, y1, x2, y2 = [int(c) for c in car_bbox]
            car_crop = frame_bgr[max(0, y1):y2, max(0, x1):x2]
            if car_crop.size == 0 or car_crop.shape[0] < 60 or car_crop.shape[1] < 60:
                continue   # crop too small — distant car, skip
            sb_results = seatbelt_model(car_crop, conf=0.40, verbose=False)
            for r in sb_results[0].boxes:
                cls_name = sb_results[0].names[int(r.cls)]
                sb_conf  = float(r.conf)
                if cls_name == "person-noseatbelt" and sb_conf >= 0.40:
                    violations.append({
                        "type":        "Seatbelt Non-Compliance",
                        "confidence":  round(sb_conf, 2),
                        "bbox":        car_bbox,
                        "track_id":    car_tid,
                        "severity":    "MEDIUM" if sb_conf < 0.75 else "HIGH",
                        "description": f"Fine-tuned model: person-noseatbelt (conf {sb_conf:.0%}). "
                                       "Human review required before enforcement.",
                    })
                    break   # one flag per car per frame is enough

    # ── 3. Stop-line / Red-light Violation ────────────────────────────────────
    # Only flag if the sidebar "Enable stop-line" toggle is ON.
    # Stop-line Y is meaningless without knowing the actual line position in the photo.
    # When disabled, this rule simply does not run — avoids false flags on
    # regular moving-traffic photos that have no painted stop line.
    stopline_enabled = st.session_state.get("stopline_enabled", False)
    seen_stopline = set()
    if stopline_enabled:
        for v_bbox, v_conf, v_tid in vehicles:
            vehicle_bottom = v_bbox[3]
            key = (round(v_bbox[0]/50), round(v_bbox[1]/50))
            if vehicle_bottom > stop_line_y and key not in seen_stopline:
                seen_stopline.add(key)
                vtype = "Red-Light Violation" if signal_red else "Stop-Line Violation"
                violations.append({
                    "type":        vtype,
                    "confidence":  round(min(v_conf + 0.02, 0.97), 2),
                    "bbox":        v_bbox,
                    "track_id":    v_tid,
                    "severity":    "CRITICAL" if signal_red else "MEDIUM",
                    "description": "Vehicle crossed stop line"
                                   + (" while signal is RED." if signal_red
                                      else " — past calibrated line."),
                })

    # ── 4. Wrong-Side Driving ─────────────────────────────────────────────────
    # Fine-tuned model (0.975 mAP50) runs on each vehicle crop.
    # Falls back to sidebar toggle heuristic if model not loaded.
    if wrongside_model is not None and frame_bgr is not None:
        seen_wrongside = set()
        for vb, vc, vt in vehicles:
            x1, y1, x2, y2 = [int(c) for c in vb]
            v_crop = frame_bgr[max(0, y1):y2, max(0, x1):x2]
            if v_crop.size == 0 or v_crop.shape[0] < 60 or v_crop.shape[1] < 60:
                continue   # crop too small — distant vehicle, skip
            ws_res = wrongside_model(v_crop, conf=0.40, verbose=False)
            for r in ws_res[0].boxes:
                cls_name = ws_res[0].names[int(r.cls)]
                ws_conf  = float(r.conf)
                if cls_name == "wrong-side" and ws_conf >= 0.40:
                    key = vt if vt is not None else tuple(int(c) // 40 for c in vb)
                    if key not in seen_wrongside:
                        seen_wrongside.add(key)
                        geo = extract_geometric_features(vb, img_shape)
                        violations.append({
                            "type":        "Wrong-Side Driving",
                            "confidence":  round(ws_conf, 2),
                            "bbox":        vb,
                            "track_id":    vt,
                            "severity":    "CRITICAL",
                            "description": f"Fine-tuned model: wrong-side (conf {ws_conf:.0%}). "
                                           "Immediate enforcement action required.",
                            "geo_features": geo,
                        })
                    break
    elif wrong_side and vehicles and scene_type != "Parking Area":
        # Sidebar toggle fallback (used when model not loaded)
        scored = []
        for vb, vc, vt in vehicles:
            geo = extract_geometric_features(vb, img_shape)
            score = geo["norm_x"] if "Right" in flow_dir else (1 - geo["norm_x"])
            scored.append((score, vb, vc, vt, geo))
        scored.sort(key=lambda s: s[0])
        if scored:
            _, vb, vc, vt, geo = scored[0]
            violations.append({
                "type":        "Wrong-Side Driving",
                "confidence":  round(min(vc + 0.03, 0.82), 2),
                "bbox":        vb,
                "track_id":    vt,
                "severity":    "CRITICAL",
                "description": (f"Heuristic (model not loaded): vehicle at x={geo['norm_x']:.2f} "
                                f"against expected flow ({flow_dir})."),
                "geo_features": geo,
            })

    # ── 6. Illegal Parking ────────────────────────────────────────────────────
    # Requires the vehicle to be GENUINELY STATIONARY across tracked frames,
    # not just in the bottom portion of the frame (which caused false positives
    # on highway footage where all vehicles appear near the bottom).
    # track_ids passed in so we can call is_stationary() per vehicle.
    # Falls back to bottom_frac heuristic in single-image mode (no track IDs).
    if scene_type != "Highway":
        stopline_bboxes = {tuple(v["bbox"]) for v in violations
                           if "Line" in v["type"] or "Light" in v["type"]}
        for v_bbox, v_conf, v_tid in parked_types:
            if tuple(v_bbox) in stopline_bboxes:
                continue
            geo = extract_geometric_features(v_bbox, img_shape)
            # In video mode: use real stationary check via this car's OWN track id
            # In image mode: tid is None, fall back to zone heuristic
            parked = False
            if v_tid is not None:
                parked = is_stationary(v_tid, v_bbox, img_w=img_shape[1])
            else:
                parked = (geo["bottom_frac"] > 0.82 and
                          geo["norm_area"] > 0.01)   # tightened threshold
            if parked:
                violations.append({
                    "type":        "Illegal Parking",
                    "confidence":  round(v_conf, 2),
                    "bbox":        v_bbox,
                    "track_id":    v_tid,
                    "severity":    "LOW",
                    "description": (
                        "Vehicle stationary across tracked frames — "
                        "confirmed via ByteTrack position history. "
                        f"Movement < 18px over last 15 frames. "
                        f"norm_area={geo['norm_area']}"
                        if track_ids else
                        "Vehicle in shoulder zone (single-image heuristic)."
                    ),
                    "geo_features": geo,
                })

    # Surface raw helmet model outputs for the Debug panel
    st.session_state["helmet_debug"] = helmet_debug
    return violations

# ── annotate frame ────────────────────────────────────────────────────────────
# Short display names so labels stay compact even on small images
LABEL_SHORT = {
    "Helmet Non-Compliance": "No Helmet",
    "Triple Riding":         "Triple Riding",
    "Red-Light Violation":   "Red Light",
    "Stop-Line Violation":   "Stop Line",
    "Wrong-Side Driving":    "Wrong Side",
    "Illegal Parking":       "Parking",
    "Seatbelt Non-Compliance": "No Seatbelt",
}

def annotate(frame: np.ndarray, violations: list) -> np.ndarray:
    out = frame.copy()
    img_h, img_w = out.shape[:2]

    color_map = {
        "CRITICAL": (0, 0, 220),
        "HIGH":     (0, 120, 255),
        "MEDIUM":   (30, 180, 255),
        "LOW":      (50, 200, 80),
    }

    font = cv2.FONT_HERSHEY_SIMPLEX
    # Fixed small scale — readable but not gigantic on any image size
    fscale    = 0.42
    fthick    = 1
    box_thick = 2

    # Track used label Y positions per column to avoid overlap
    used_y: dict[int, int] = {}   # x1 → last used label bottom y

    for v in violations:
        x1, y1, x2, y2 = [int(c) for c in v["bbox"]]
        col = color_map.get(v["severity"], (0, 200, 0))

        # Draw thin bounding box
        cv2.rectangle(out, (x1, y1), (x2, y2), col, box_thick)

        # Compact label: short name + confidence %
        short = LABEL_SHORT.get(v["type"], v["type"].split()[0])
        label = f"{short} {v['confidence']:.0%}"
        (tw, th), bl = cv2.getTextSize(label, font, fscale, fthick)

        # Place label above box; push down if another label already occupies that slot
        col_key = x1 // 60   # bucket overlapping boxes into same column group
        min_y = used_y.get(col_key, 0)
        label_top = max(y1 - th - bl - 4, min_y + 2)
        if label_top < th + 4:
            label_top = y2 + 4   # flip below the box if no room above

        # Semi-transparent background rectangle
        overlay = out.copy()
        cv2.rectangle(overlay,
                      (x1, label_top),
                      (x1 + tw + 6, label_top + th + bl + 4),
                      col, -1)
        cv2.addWeighted(overlay, 0.75, out, 0.25, 0, out)

        # White text for max contrast
        cv2.putText(out, label,
                    (x1 + 3, label_top + th + 1),
                    font, fscale, (255, 255, 255), fthick,
                    lineType=cv2.LINE_AA)

        used_y[col_key] = label_top + th + bl + 6

    # Small banner — top-left, thin strip
    banner = f"ViolaVision 2.0  |  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    bw, bh = cv2.getTextSize(banner, font, 0.38, 1)[0]
    cv2.rectangle(out, (0, 0), (bw + 10, bh + 8), (15, 15, 15), -1)
    cv2.putText(out, banner, (5, bh + 3), font, 0.38, (200, 200, 200), 1,
                lineType=cv2.LINE_AA)

    return out

# ── licence plate OCR ─────────────────────────────────────────────────────────
_PLATE_RE = re.compile(r"^[A-Z]{2}[0-9]{2}[A-Z]{1,3}[0-9]{3,4}$")

def _read_plate_from_img(img: np.ndarray, ocr_reader) -> str:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255,
                              cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    for _, text, conf in ocr_reader.readtext(thresh):
        cleaned = re.sub(r"[^A-Z0-9]", "", text.upper())
        if _PLATE_RE.match(cleaned) and conf > 0.4:
            return cleaned
    return "UNREADABLE"

def extract_plate(frame: np.ndarray, ocr_reader) -> str | None:
    """Full-frame OCR — used in single-image mode."""
    return _read_plate_from_img(frame, ocr_reader)

def extract_plate_cropped(frame: np.ndarray, bbox, ocr_reader) -> str:
    """
    OCR only the vehicle's bounding box (with padding) instead of the whole
    frame. A small crop is 5-15x faster on CPU — this is what keeps the live
    video feed from freezing for seconds every time a violation confirms.
    """
    x1, y1, x2, y2 = [int(c) for c in bbox]
    h, w = frame.shape[:2]
    pad = 8
    crop = frame[max(0, y1 - pad):min(h, y2 + pad),
                 max(0, x1 - pad):min(w, x2 + pad)]
    if crop.size == 0 or crop.shape[0] < 12 or crop.shape[1] < 12:
        return "UNREADABLE"
    return _read_plate_from_img(crop, ocr_reader)

# ── plate-colour → vehicle category ──────────────────────────────────────────
def classify_plate_category(vehicle_crop: np.ndarray) -> str:
    """
    Indian plate colour standard:
      White  → Private vehicle
      Yellow → Commercial / taxi
      Green  → Electric vehicle
      Blue   → Government / embassy
    Returns a human-readable category string.
    """
    if vehicle_crop is None or vehicle_crop.size == 0:
        return "Unknown"
    hsv = cv2.cvtColor(vehicle_crop, cv2.COLOR_BGR2HSV)
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


# ── Neo4j graph layer (falls back to SQLite if Neo4j not available) ───────────
class ViolationGraph:
    """
    Thin graph layer. Uses Neo4j when available; falls back to equivalent
    SQLite queries so the app always works without a running Neo4j instance.
    """
    def __init__(self, conn_sqlite,
                 uri="bolt://localhost:7687",
                 user="neo4j", password="violavision"):
        self._sq = conn_sqlite
        self._driver = None
        if _NEO4J_AVAILABLE:
            try:
                drv = _Neo4jDriver.driver(uri, auth=(user, password))
                drv.verify_connectivity()
                self._driver = drv
                self._ensure_indexes()
            except Exception:
                self._driver = None   # Neo4j not reachable — use SQLite

    @property
    def backend(self):
        return "Neo4j" if self._driver else "SQLite (Neo4j fallback)"

    def _ensure_indexes(self):
        with self._driver.session() as s:
            s.run("CREATE CONSTRAINT IF NOT EXISTS FOR (v:Vehicle) REQUIRE v.plate IS UNIQUE")

    def add_violation(self, plate: str, violation_type: str,
                      location: str, timestamp: float):
        if not plate or plate == "UNREADABLE":
            return
        if self._driver:
            with self._driver.session() as s:
                s.run("""
                    MERGE (v:Vehicle {plate: $plate})
                    MERGE (l:Location {name: $location})
                    CREATE (e:Violation {type: $vtype, timestamp: $ts})
                    MERGE (v)-[:COMMITTED]->(e)
                    MERGE (e)-[:OCCURRED_AT]->(l)
                """, plate=plate, location=location, vtype=violation_type, ts=timestamp)
        # SQLite path: already written by save_violation() — nothing extra needed

    def repeat_offenders(self, min_count: int = 2):
        if self._driver:
            with self._driver.session() as s:
                res = s.run("""
                    MATCH (v:Vehicle)-[:COMMITTED]->(e:Violation)
                    WITH v.plate AS plate, count(e) AS violations,
                         collect(DISTINCT e.type) AS types
                    WHERE violations >= $min
                    RETURN plate, violations, types ORDER BY violations DESC
                """, min=min_count)
                return [(r["plate"], r["violations"],
                         ", ".join(r["types"])) for r in res]
        # SQLite fallback
        thirty_ago = (datetime.now() - timedelta(days=30)).timestamp()
        cur = self._sq.cursor()
        cur.execute("""
            SELECT plate_number, COUNT(*) as cnt,
                   GROUP_CONCAT(DISTINCT violation_type)
            FROM violations WHERE timestamp > ? AND plate_number != 'UNREADABLE'
            GROUP BY plate_number HAVING cnt >= ?
            ORDER BY cnt DESC""", (thirty_ago, min_count))
        return cur.fetchall()

    def plate_cloning_check(self, plate: str, current_location: str,
                             window_minutes: int = 10):
        """Return recent sightings of this plate at OTHER locations in the window."""
        if self._driver:
            cutoff = time.time() - window_minutes * 60
            with self._driver.session() as s:
                res = s.run("""
                    MATCH (v:Vehicle {plate: $plate})-[:COMMITTED]->(e:Violation)
                          -[:OCCURRED_AT]->(l:Location)
                    WHERE l.name <> $loc AND e.timestamp > $cutoff
                    RETURN l.name AS location, e.timestamp AS ts
                    ORDER BY e.timestamp DESC LIMIT 5
                """, plate=plate, loc=current_location, cutoff=cutoff)
                return [dict(r) for r in res]
        # SQLite fallback
        cutoff = time.time() - window_minutes * 60
        cur = self._sq.cursor()
        cur.execute("""
            SELECT camera_id, timestamp FROM violations
            WHERE plate_number=? AND camera_id!=? AND timestamp>?
            ORDER BY timestamp DESC LIMIT 5""",
            (plate, current_location, cutoff))
        rows = cur.fetchall()
        return [{"location": r[0], "ts": r[1]} for r in rows]

    def close(self):
        if self._driver:
            self._driver.close()


# ── evidence generation ───────────────────────────────────────────────────────
def generate_evidence(frame, annotated_frame, violation,
                       plate, camera_id, private_key):
    _, img_bytes     = cv2.imencode(".jpg", annotated_frame)
    _, orig_bytes    = cv2.imencode(".jpg", frame)
    img_b64  = base64.b64encode(img_bytes.tobytes()).decode()
    orig_b64 = base64.b64encode(orig_bytes.tobytes()).decode()

    record = {
        "schema_version":    "2.0",
        "timestamp_unix":    time.time(),
        "timestamp_human":   datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "camera_id":         camera_id,
        "gps_latitude":      12.9165,   # Silk Board (demo)
        "gps_longitude":     77.6229,
        "violation_type":    violation["type"],
        "violation_severity":violation["severity"],
        "confidence_score":  violation["confidence"],
        "plate_number":      plate or "UNREADABLE",
        "annotated_image_b64": img_b64,
        "original_image_b64":  orig_b64,
        "system_version":    "ViolaVision-2.0-prototype",
        "note":              "Prototype: software signing. Production: HSM/TPM chip.",
    }

    record_str  = json.dumps(record, sort_keys=True)
    record_hash = hashlib.sha256(record_str.encode()).hexdigest()

    signature = private_key.sign(
        record_hash.encode(),
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256())

    record["sha256_hash"]       = record_hash
    record["digital_signature"] = base64.b64encode(signature).decode()
    record["blockchain_anchor"] = f"MOCK-TX-{record_hash[:16].upper()}"
    record["verification_note"] = (
        "Verify with ViolaVision public key. "
        "Hash anchored to Polygon blockchain in production.")
    return record

def verify_evidence(record: dict, private_key) -> tuple[bool, str]:
    pub = private_key.public_key()
    stored_hash = record.get("sha256_hash")
    stored_sig  = record.get("digital_signature")
    if not stored_hash or not stored_sig:
        return False, "Missing hash or signature"
    check = {k: v for k, v in record.items()
             if k not in {"sha256_hash", "digital_signature",
                          "blockchain_anchor", "verification_note"}}
    computed = hashlib.sha256(
        json.dumps(check, sort_keys=True).encode()).hexdigest()
    if computed != stored_hash:
        return False, "TAMPERED — hash mismatch"
    try:
        pub.verify(
            base64.b64decode(stored_sig),
            stored_hash.encode(),
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256())
        return True, "VERIFIED — record integrity confirmed"
    except Exception:
        return False, "TAMPERED — signature invalid"

# ── priority scoring ──────────────────────────────────────────────────────────
VIOLATION_WEIGHTS = {
    "Red-Light Violation":        10.0,
    "Wrong-Side Driving":         10.0,
    "Triple Riding":               8.0,
    "Helmet Non-Compliance":       7.0,
    "Stop-Line Violation":         6.0,
    "Seatbelt Non-Compliance":     6.0,
    "Footpath/Zebra Encroachment": 5.0,
    "Illegal Parking":             3.0,
}
LOCATION_WEIGHTS = {
    "silk_board": 1.5, "kr_circle": 1.4,
    "hebbal": 1.3, "marathahalli": 1.3,
    "whitefield": 1.2,
}

def priority_score(violation_type: str, camera_id: str,
                   plate: str, conn: sqlite3.Connection):
    v_w = VIOLATION_WEIGHTS.get(violation_type, 3.0)
    l_w = next((w for loc, w in LOCATION_WEIGHTS.items()
                if loc in camera_id.lower()), 1.0)
    h = datetime.now().hour
    t_w = 1.4 if (7 <= h <= 10 or 17 <= h <= 20) else (1.3 if (h >= 22 or h <= 5) else 1.0)

    thirty_ago = (datetime.now() - timedelta(days=30)).timestamp()
    cur = conn.cursor()
    # Only count repeats for real, readable plates — UNREADABLE must never accumulate
    if plate and plate != "UNREADABLE" and len(plate) >= 6:
        cur.execute(
            "SELECT COUNT(*) FROM violations "
            "WHERE plate_number=? AND plate_number!='UNREADABLE' AND timestamp>?",
            (plate, thirty_ago))
        repeat = cur.fetchone()[0]
    else:
        repeat = 0
    r_w = 1.0 if repeat == 0 else (1.5 if repeat < 3 else (2.0 if repeat < 7 else 3.0))

    total = round(v_w * l_w * t_w * r_w, 2)
    if total >= 25:
        level, action = "CRITICAL", "Auto-challan + supervisor alert"
    elif total >= 15:
        level, action = "HIGH", "Auto-challan + 1-hour review"
    elif total >= 8:
        level, action = "MEDIUM", "Human review queue — same day"
    else:
        level, action = "LOW", "Batch review — weekly"
    if repeat >= 7:
        action += " | SERIAL OFFENDER — refer to RTO"
    return total, level, action, repeat

def save_violation(conn, record, priority, level, camera_id, plate,
                   snapshot_path=None):
    conn.execute("""
        INSERT INTO violations
        (timestamp,plate_number,violation_type,confidence,
         priority_score,priority_level,evidence_hash,camera_id,snapshot_path)
        VALUES(?,?,?,?,?,?,?,?,?)""",
        (record["timestamp_unix"], plate,
         record["violation_type"], record["confidence_score"],
         priority, level, record["sha256_hash"], camera_id, snapshot_path))
    conn.commit()

# ── evidence snapshots (human-reviewable proof on disk) ────────────────────────
SNAP_DIR = os.path.join(BASE_DIR, "evidence_store", "snapshots")
os.makedirs(SNAP_DIR, exist_ok=True)

def save_snapshot(annotated_full_bgr, crop_bgr, evidence_hash):
    """
    Write the exact-moment evidence to disk so a human can cross-check it.
      *_full.jpg — the whole annotated frame (box + label + timestamp banner)
      *_crop.jpg — a zoomed crop of just the offending object
    Returns the full-frame path (stored in the DB and shown in the Review Queue).
    """
    base      = os.path.join(SNAP_DIR, evidence_hash[:16])
    full_path = base + "_full.jpg"
    crop_path = base + "_crop.jpg"
    cv2.imwrite(full_path, annotated_full_bgr)
    if crop_bgr is not None and getattr(crop_bgr, "size", 0):
        # upscale tiny crops so the reviewer can actually see the rider/plate
        c = crop_bgr
        if min(c.shape[:2]) < 160:
            s = max(2, int(220 / max(min(c.shape[:2]), 1)))
            c = cv2.resize(c, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC)
        cv2.imwrite(crop_path, c)
    return full_path

# ── MOCK VAHAN lookup ─────────────────────────────────────────────────────────
VAHAN_DB = {
    "KA01AB1234": {"owner": "Ramesh Kumar",   "address": "BTM Layout, Bengaluru",
                   "vehicle": "Honda Activa 6G",  "insurance": "Valid"},
    "KA05MJ2847": {"owner": "Priya Sharma",   "address": "Koramangala, Bengaluru",
                   "vehicle": "TVS Jupiter",      "insurance": "Valid"},
    "MH02XY9999": {"owner": "Amit Desai",     "address": "Pune, Maharashtra",
                   "vehicle": "Bajaj Pulsar 150", "insurance": "Expired"},
}

def vahan_lookup(plate: str) -> dict:
    return VAHAN_DB.get(plate, {
        "owner": "Unknown — VAHAN query required",
        "address": "N/A", "vehicle": "Unknown", "insurance": "Unknown"})

# ── knowledge graph queries (pure SQL, no Neo4j dep for prototype) ─────────────
def kg_repeat_offenders(conn):
    thirty_ago = (datetime.now() - timedelta(days=30)).timestamp()
    cur = conn.cursor()
    cur.execute("""
        SELECT plate_number, COUNT(*) as cnt,
               GROUP_CONCAT(DISTINCT violation_type) as types
        FROM violations
        WHERE timestamp > ? AND plate_number != 'UNREADABLE'
              AND LENGTH(plate_number) >= 6
        GROUP BY plate_number HAVING cnt >= 2
        ORDER BY cnt DESC""", (thirty_ago,))
    return cur.fetchall()

def kg_hotspots(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT camera_id, COUNT(*) as cnt,
               AVG(priority_score) as avg_priority
        FROM violations GROUP BY camera_id
        ORDER BY cnt DESC""")
    return cur.fetchall()

# ── init ──────────────────────────────────────────────────────────────────────
conn        = init_db()
private_key = get_signing_key()
vgraph      = ViolationGraph(conn)   # Neo4j if available, else SQLite fallback

# ── sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    # ── Logo ──────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="vv-logo">
      <span class="mark"></span>
      <span class="word">ViolaVision</span>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    # ── System Status ──────────────────────────────────────────────────────
    st.markdown('<div class="vv-menu-label">System Status</div>', unsafe_allow_html=True)
    models_loaded = sum([
        os.path.exists(HELMET_MODEL_PATH),
        os.path.exists(SEATBELT_MODEL_PATH),
        os.path.exists(WRONGSIDE_MODEL_PATH),
    ])
    _sb1, _sb2 = st.columns(2)
    _sb1.metric("Feed", "Live")
    _sb2.metric("Models", f"{models_loaded+1}/4")
    st.divider()

    # ── Camera Config ──────────────────────────────────────────────────────
    st.markdown('<div class="vv-menu-label">Camera Config</div>', unsafe_allow_html=True)
    _CAMERA_LABELS = {
        "Silk Board Junction — Bengaluru": "silk_board_junction",
        "KR Circle — Bengaluru":           "kr_circle",
        "Hebbal Flyover — Bengaluru":      "hebbal_flyover",
        "Marathahalli Bridge — Bengaluru": "marathahalli_bridge",
        "Whitefield Signal — Bengaluru":   "whitefield_01",
    }
    _cam_label = st.selectbox("Camera Location", list(_CAMERA_LABELS.keys()))
    camera_id  = _CAMERA_LABELS[_cam_label]
    st.session_state["scene_type"] = st.radio(
        "Scene Type", ["Junction", "Parking Area", "Highway"],
        help="Suppresses irrelevant violations per scene context")
    st.divider()

    # ── Detection ─────────────────────────────────────────────────────────
    st.markdown('<div class="vv-menu-label">Detection</div>', unsafe_allow_html=True)
    st.session_state["signal_red"] = st.toggle("Signal is RED", value=False,
        help="CRITICAL severity for stop-line violations")
    st.session_state["stopline_enabled"] = st.toggle("Stop-line detection", value=False,
        help="Only enable when a painted stop line is visible")
    stop_line_y = st.slider("Stop-line Y (px)", 200, 600, 400)
    st.session_state["preprocessing_on"] = st.toggle("CLAHE + Dehaze", value=True,
        help="Improves detection in rain/haze/low-light")
    st.session_state["park_min_frames"] = st.slider("Parking min frames", 30, 120, 60)
    st.divider()

    # ── Wrong-Side ────────────────────────────────────────────────────────
    st.markdown('<div class="vv-menu-label">Wrong-Side</div>', unsafe_allow_html=True)
    st.session_state["wrong_side_present"] = st.toggle("Wrong-side vehicle", value=False)
    st.session_state["flow_direction"] = st.radio("Expected flow",
        ["Left → Right", "Right → Left"])
    st.divider()

    # ── DB counters ───────────────────────────────────────────────────────
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM violations"); total_v = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM violations WHERE operator_action IS NULL"); pending = cur.fetchone()[0]
    _sb3, _sb4 = st.columns(2)
    _sb3.metric("Total", total_v)
    _sb4.metric("Pending", pending)

    st.markdown(f"""
    <div style="background:#111111; border-radius:28px; padding:1.2rem; margin-top:1.1rem; color:#ffffff; position:relative; overflow:hidden;">
      <div style="width:38px; height:38px; border-radius:12px; background:rgba(255,255,255,0.08); display:flex; align-items:center; justify-content:center; font-size:1.15rem; margin-bottom:0.9rem;">
        📷
      </div>
      <p style="font-family:'Outfit',sans-serif; font-weight:600; font-size:0.92rem; margin:0; line-height:1.2; color:#ffffff;">ViolaVision Engine</p>
      <p style="font-size:0.68rem; color:rgba(255,255,255,0.4); margin:4px 0 14px 0; line-height:1.35;">4-model CV pipeline · ByteTrack · signed evidence</p>
      <button style="width:100%; border:none; background:#ffffff; color:#111111; border-radius:9999px; font-size:0.65rem; font-weight:700; letter-spacing:0.08em; text-transform:uppercase; cursor:pointer; padding: 9px 0; transition: background 0.2s;">
        Active · {models_loaded + 1}/4 Models
      </button>
    </div>
    """, unsafe_allow_html=True)

# ── main tabs ─────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Live Detection",
    "Review Queue",
    "Analytics",
    "Knowledge Graph",
    "Evidence Verify",
])

# ── temporal tracking state (per session) ────────────────────────────────────
if "vio_history"      not in st.session_state:
    st.session_state.vio_history      = defaultdict(lambda: deque(maxlen=5))
if "confirmed_ids"    not in st.session_state:
    st.session_state.confirmed_ids    = set()
if "live_log"         not in st.session_state:
    st.session_state.live_log         = []
if "pending_evidence" not in st.session_state:
    st.session_state.pending_evidence = []
if "vehicle_positions" not in st.session_state:
    # track_id → deque of (cx, cy) centroids across last 90 processed frames
    # At skip_n=3 on 30fps source = ~9 seconds of real time before parking fires
    st.session_state.vehicle_positions = defaultdict(lambda: deque(maxlen=90))

def is_stationary(track_id: int, bbox: list,
                  move_threshold_px: float = 20.0,
                  img_w: int = 1280) -> bool:
    """
    Vehicles near the frame edge (side of road, shoulder) need fewer frames
    to be declared parked — they are unlikely to be junction traffic.
    Vehicles in the centre lanes need more frames to avoid flagging red-light stops.

    Edge zone  (norm_x < 0.12 or > 0.88): requires 25 frames  (~2.5 sec)
    Centre zone (everything else):          requires park_min_frames (default 60)
    """
    cx = (bbox[0] + bbox[2]) / 2
    cy = (bbox[1] + bbox[3]) / 2
    st.session_state.vehicle_positions[track_id].append((cx, cy))
    history = list(st.session_state.vehicle_positions[track_id])

    norm_x = cx / max(img_w, 1)
    near_edge = norm_x < 0.20 or norm_x > 0.80   # outer 20% = shoulder/side lane
    min_frames = 25 if near_edge else st.session_state.get("park_min_frames", 60)

    if len(history) < min_frames:
        return False
    xs = [p[0] for p in history]
    ys = [p[1] for p in history]
    total_movement = ((max(xs) - min(xs))**2 + (max(ys) - min(ys))**2) ** 0.5
    return total_movement < move_threshold_px

def temporal_confirm(track_id: int, vio_type: str, flagged: bool) -> bool:
    """3-of-5 frame confirmation. Returns True once threshold is met."""
    key = (track_id, vio_type)
    st.session_state.vio_history[key].append(1 if flagged else 0)
    return sum(st.session_state.vio_history[key]) >= 3

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — Live Detection (image mode) + Video Feed mode
# ─────────────────────────────────────────────────────────────────────────────
with tab1:
    # ── Page title (Elysium-style) ─────────────────────────────────────────
    st.markdown("""
    <div style="margin-bottom:1.4rem">
      <p style="font-size:0.62rem;font-weight:700;letter-spacing:0.18em;text-transform:uppercase;color:rgba(0,0,0,0.25);margin-bottom:4px">Detection Pipeline</p>
      <h1 style="font-family:'Outfit',sans-serif;font-size:2rem;font-weight:700;letter-spacing:-0.03em;color:#111111;margin:0">Live Analysis</h1>
      <p style="font-size:0.8rem;color:rgba(0,0,0,0.35);margin-top:4px">Real-time traffic violation detection · ByteTrack · temporal 3-of-5 confirmation</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Stat cards row (4-wide bento grid) ────────────────────────────────
    cur_stat = conn.cursor()
    cur_stat.execute("SELECT COUNT(*) FROM violations")
    _total = cur_stat.fetchone()[0]
    cur_stat.execute("SELECT COUNT(*) FROM violations WHERE operator_action IS NULL")
    _pending = cur_stat.fetchone()[0]
    cur_stat.execute("SELECT COUNT(DISTINCT plate_number) FROM violations WHERE plate_number!='UNREADABLE'")
    _plates = cur_stat.fetchone()[0]

    _s1, _s2, _s3, _s4 = st.columns(4)
    with _s1:
        with st.container(border=True):
            st.markdown('<p style="font-size:0.6rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:rgba(0,0,0,0.25);margin-bottom:2px">Total Violations</p>', unsafe_allow_html=True)
            st.markdown(f'<p style="font-family:\'Outfit\',sans-serif;font-size:2.2rem;font-weight:600;letter-spacing:-0.03em;color:#111;margin:0">{_total}</p>', unsafe_allow_html=True)
            st.caption("All time · all cameras")
    with _s2:
        with st.container(border=True):
            st.markdown('<p style="font-size:0.6rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:rgba(0,0,0,0.25);margin-bottom:2px">Pending Review</p>', unsafe_allow_html=True)
            st.markdown(f'<p style="font-family:\'Outfit\',sans-serif;font-size:2.2rem;font-weight:600;letter-spacing:-0.03em;color:#111;margin:0">{_pending}</p>', unsafe_allow_html=True)
            st.caption("Awaiting operator action")
    with _s3:
        with st.container(border=True):
            st.markdown('<p style="font-size:0.6rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:rgba(0,0,0,0.25);margin-bottom:2px">Unique Plates</p>', unsafe_allow_html=True)
            st.markdown(f'<p style="font-family:\'Outfit\',sans-serif;font-size:2.2rem;font-weight:600;letter-spacing:-0.03em;color:#111;margin:0">{_plates}</p>', unsafe_allow_html=True)
            st.caption("Recognised this session")
    with _s4:
        with st.container(border=True):
            st.markdown('<p style="font-size:0.6rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:rgba(0,0,0,0.25);margin-bottom:2px">Models Active</p>', unsafe_allow_html=True)
            st.markdown(f'<p style="font-family:\'Outfit\',sans-serif;font-size:2.2rem;font-weight:600;letter-spacing:-0.03em;color:#111;margin:0">{models_loaded+1}<span style="font-size:1rem;opacity:0.3"> / 4</span></p>', unsafe_allow_html=True)
            st.caption("YOLO · Helmet · Seatbelt · WrongSide")

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── Input mode selector card ───────────────────────────────────────────
    with st.container(border=True):
        st.markdown('<p style="font-size:0.6rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:rgba(0,0,0,0.25);margin-bottom:8px">Input Mode</p>', unsafe_allow_html=True)
        input_mode = st.radio(
            "Select source",
            ["📷 Single image", "🎥 Video feed (tracking)"],
            horizontal=True, label_visibility="collapsed")

    # ── helpers shared by both modes ──────────────────────────────────────────
    def _show_violation_table(violations, plate, cam_id):
        """Render violation rows and return the primary evidence record."""
        vahan = vahan_lookup(plate or "")
        rows  = []
        for v in violations:
            sc, lv, act, rep = priority_score(v["type"], cam_id, plate or "", conn)
            rows.append({
                "Violation":  v["type"],
                "Conf":       f"{v['confidence']:.0%}",
                "Severity":   v["severity"],
                "Plate":      plate or "UNREADABLE",
                "Owner":      vahan["owner"],
                "Score":      sc,
                "Level":      lv,
                "Action":     act,
                "Repeat 30d": rep,
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
        return vahan

    # ─────────────────────────────────────────────────────────────────────────
    # MODE A — Single image
    # ─────────────────────────────────────────────────────────────────────────
    if input_mode == "📷 Single image":
        with st.container(border=True):
            st.markdown('<p style="font-size:0.6rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:rgba(0,0,0,0.25);margin-bottom:6px">Upload Frame</p>', unsafe_allow_html=True)
            st.caption("Upload one frame — useful for quick testing of any violation type.")
            uploaded = st.file_uploader(
                "Upload traffic image", type=["jpg", "jpeg", "png"], label_visibility="collapsed")

        if uploaded:
            file_bytes = np.frombuffer(uploaded.read(), np.uint8)
            frame_bgr  = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            frame_bgr  = preprocess(frame_bgr, st.session_state.get("preprocessing_on", True))

            with st.spinner("Running detection pipeline…"):
                yolo            = get_yolo()
                helmet_model    = get_helmet_yolo()
                seatbelt_model  = get_seatbelt_yolo()
                wrongside_model = get_wrongside_yolo()
                ocr             = get_ocr()
                results         = yolo(frame_bgr, verbose=False)
                violations      = detect_violations(
                    results, stop_line_y, frame_bgr.shape[:2],
                    frame_bgr=frame_bgr, helmet_model=helmet_model,
                    seatbelt_model=seatbelt_model, wrongside_model=wrongside_model)
                plate     = extract_plate(frame_bgr, ocr)
                annotated = annotate(frame_bgr, violations)

            col1, col2 = st.columns(2)
            col1.image(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB),
                       caption="Original (preprocessed)", use_container_width=True)
            col2.image(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB),
                       caption="Detected Violations", use_container_width=True)

            if not violations:
                st.success("No violations detected in this frame.")
            else:
                st.subheader(f"Detected {len(violations)} Violation(s)")
                vahan = _show_violation_table(violations, plate, camera_id)

                primary_v = violations[0]
                evidence  = generate_evidence(
                    frame_bgr, annotated, primary_v,
                    plate, camera_id, private_key)
                sc, lv, _, _ = priority_score(
                    primary_v["type"], camera_id, plate or "", conn)
                bxp = [int(c) for c in primary_v["bbox"]]
                pcrop = frame_bgr[max(0, bxp[1]):bxp[3], max(0, bxp[0]):bxp[2]]
                snap = save_snapshot(annotated, pcrop, evidence["sha256_hash"])
                save_violation(conn, evidence, sc, lv, camera_id, plate or "",
                               snapshot_path=snap)

                st.subheader("Evidence Record (Primary Violation)")
                st.json({k: v for k, v in evidence.items()
                         if k not in {"annotated_image_b64", "original_image_b64"}})

                st.subheader("VAHAN Owner Lookup (Mock)")
                vc1, vc2, vc3, vc4 = st.columns(4)
                vc1.metric("Owner",     vahan["owner"])
                vc2.metric("Vehicle",   vahan["vehicle"])
                vc3.metric("Address",   vahan["address"])
                vc4.metric("Insurance", vahan["insurance"])

                st.session_state["last_evidence"] = evidence

    # ─────────────────────────────────────────────────────────────────────────
    # MODE B — Video feed with ByteTrack object tracking
    # ─────────────────────────────────────────────────────────────────────────
    else:
        # ── Bento row: Video Source | Pipeline Config | Analysis Options ──
        _vc1, _vc2, _vc3 = st.columns([1.2, 1, 1])

        demo_path        = os.path.join(BASE_DIR, "data", "demo_traffic.mp4")
        demo_helmet_path = os.path.join(BASE_DIR, "data", "demo_helmet.mp4")
        has_demo        = os.path.exists(demo_path)
        has_helmet_demo = os.path.exists(demo_helmet_path)
        demo_options = []
        if has_helmet_demo:
            demo_options.append("🏍 Indian traffic (helmet test)")
        if has_demo:
            demo_options.append("▶ Demo video (highway)")
        demo_options.append("📁 Upload MP4 / AVI")

        with _vc1:
            with st.container(border=True):
                st.markdown('<p style="font-size:0.6rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:rgba(0,0,0,0.25);margin-bottom:6px">Video Source</p>', unsafe_allow_html=True)
                st.caption("ByteTrack · 3-of-5 temporal confirmation · identical to live CCTV")
                video_src = st.radio("Video source", demo_options, horizontal=False, label_visibility="collapsed")
                video_path = None
                if video_src.startswith("🏍"):
                    video_path = demo_helmet_path
                elif video_src.startswith("▶"):
                    video_path = demo_path
                else:
                    uv = st.file_uploader("Upload traffic video", type=["mp4", "avi", "mov"], label_visibility="collapsed")
                    if uv:
                        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4", dir=BASE_DIR)
                        tmp.write(uv.read()); tmp.flush()
                        video_path = tmp.name

        with _vc2:
            with st.container(border=True):
                st.markdown('<p style="font-size:0.6rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:rgba(0,0,0,0.25);margin-bottom:6px">Pipeline Config</p>', unsafe_allow_html=True)
                skip_n = st.slider("Frame skip (speed vs detail)", 1, 10, 4,
                    help="4 = ~7.5 FPS effective. Seatbelt + wrong-side run every 2nd processed frame.")
                max_secs = st.slider("Max seconds to process", 10, 120, 45)

        with _vc3:
            with st.container(border=True):
                st.markdown('<p style="font-size:0.6rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:rgba(0,0,0,0.25);margin-bottom:6px">Analysis Options</p>', unsafe_allow_html=True)
                smooth_mode = st.toggle("Smooth live mode", value=True,
                    help="Defers OCR + signing to batch at end. Keeps display fluid.")
                debug_mode  = st.toggle("Diagnostics", value=False,
                    help="Show per-frame model output panel.")
                use_rtdetr  = st.toggle("RT-DETR verify", value=False,
                    help="Second-stage cascade verifier. Reduces false positives, slower.")

        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

        # ── Action card (black tile like Elysium's Run Discovery) ─────────
        _a1, _a2 = st.columns([1, 2])
        with _a1:
            st.markdown("""
            <div style="background:#111111;border-radius:22px;padding:1.4rem 1.5rem;min-height:130px;display:flex;flex-direction:column;justify-content:space-between">
              <p style="font-size:0.58rem;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;color:rgba(255,255,255,0.35);margin:0">Action</p>
              <p style="font-family:'Outfit',sans-serif;font-size:1.3rem;font-weight:600;color:#fff;margin:0.6rem 0 0 0">Start Analysis</p>
              <p style="font-size:0.68rem;color:rgba(255,255,255,0.35);margin:4px 0 0 0">ByteTrack · temporal confirmation · signed evidence</p>
            </div>
            """, unsafe_allow_html=True)

        _run_btn = st.button("▶ Start Video Analysis", type="primary", use_container_width=False)

        if video_path and _run_btn:
            # Reset tracking state for fresh run
            st.session_state.vio_history      = defaultdict(lambda: deque(maxlen=5))
            st.session_state.confirmed_ids    = set()
            st.session_state.live_log         = []
            st.session_state.pending_evidence = []
            st.session_state.vehicle_positions = defaultdict(lambda: deque(maxlen=90))

            yolo            = get_yolo()
            helmet_model    = get_helmet_yolo()
            seatbelt_model  = get_seatbelt_yolo()
            wrongside_model = get_wrongside_yolo()
            ocr             = get_ocr()
            rtdetr          = get_rtdetr() if use_rtdetr else None

            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS) or 25
            total_frames = int(fps * max_secs)

            col_vid, col_log = st.columns([3, 2])
            frame_slot   = col_vid.empty()
            counter_slot = col_vid.empty()
            log_slot     = col_log.empty()

            col_vid.markdown('<p style="font-size:0.68rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#6b7280;margin-bottom:6px">LIVE FEED — BYTRETRACK ACTIVE</p>', unsafe_allow_html=True)
            col_log.markdown('<p style="font-size:0.68rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#6b7280;margin-bottom:6px">CONFIRMED VIOLATIONS</p>', unsafe_allow_html=True)
            debug_slot = col_vid.empty() if debug_mode else None

            frame_idx   = 0
            processed   = 0
            stop_button = st.button("⏹ Stop")

            while cap.isOpened() and frame_idx < total_frames and not stop_button:
                ret, frame_bgr = cap.read()
                if not ret:
                    break
                frame_idx += 1

                # Skip frames for performance
                if frame_idx % skip_n != 0:
                    continue

                frame_bgr = preprocess(frame_bgr, st.session_state.get("preprocessing_on", True))
                processed += 1

                # ByteTrack: persist=True keeps IDs stable across frames
                track_results = yolo.track(
                    frame_bgr, persist=True,
                    conf=0.40, verbose=False)

                # Extract track IDs before detect_violations so parking
                # check can use real stationary detection
                boxes = track_results[0].boxes
                ids   = (boxes.id.int().tolist()
                         if boxes.id is not None else [])

                # Run secondary classifiers (seatbelt, wrong-side) every 2nd
                # processed frame only — temporal confirmation needs 3-of-5
                # so we still accumulate enough votes, with half the inference cost.
                run_secondary = (processed % 2 == 0)
                violations = detect_violations(
                    track_results, stop_line_y, frame_bgr.shape[:2],
                    frame_bgr=frame_bgr, helmet_model=helmet_model,
                    track_ids=ids,
                    seatbelt_model=seatbelt_model  if run_secondary else None,
                    wrongside_model=wrongside_model if run_secondary else None)

                # ── Temporal confirmation per tracked object ───────────────

                new_confirmations = []
                for v in violations:
                    # Use the violation's OWN tracked object id (stable across frames).
                    # Fall back to a quantised position key only if tracking gave None.
                    tid = v.get("track_id")
                    if tid is None:
                        bx = v["bbox"]
                        tid = -(int((bx[0] + bx[2]) / 80) * 1000
                                + int((bx[1] + bx[3]) / 80))
                    if temporal_confirm(tid, v["type"], True):
                        uid = (tid, v["type"])
                        if uid not in st.session_state.confirmed_ids:
                            # ── RT-DETR second-stage verification ──────────
                            # Confirm the crop really contains the expected
                            # object before logging. Rejects YOLO hallucinations.
                            if use_rtdetr:
                                bx0 = [int(c) for c in v["bbox"]]
                                vcrop = frame_bgr[max(0, bx0[1]):bx0[3],
                                                  max(0, bx0[0]):bx0[2]]
                                if not rtdetr_confirms(vcrop, v["type"], rtdetr):
                                    continue   # verifier rejected — skip as FP

                            st.session_state.confirmed_ids.add(uid)

                            if smooth_mode:
                                # Smooth live mode: defer OCR + evidence to end of run.
                                # Store half-res frame to keep RAM low with 3 models running.
                                bx = [int(c) for c in v["bbox"]]
                                pad = 6
                                crop = frame_bgr[max(0, bx[1]-pad):bx[3]+pad,
                                                 max(0, bx[0]-pad):bx[2]+pad].copy()
                                h, w = frame_bgr.shape[:2]
                                small_frame = cv2.resize(frame_bgr, (w // 2, h // 2))
                                st.session_state.pending_evidence.append({
                                    "violation":  v,
                                    "frame":      small_frame,
                                    "crop":       crop,
                                    "tid":        tid,
                                    "time":       datetime.now().strftime("%H:%M:%S"),
                                })
                                st.session_state.live_log.append({
                                    "Time":      datetime.now().strftime("%H:%M:%S"),
                                    "Track ID":  tid,
                                    "Violation": v["type"],
                                    "Conf":      f"{v['confidence']:.0%}",
                                    "Score":     "—",
                                    "Level":     v["severity"],
                                    "Action":    "queued",
                                    "Plate":     "⏳ pending",
                                    "Status":    "⏳ PENDING REVIEW",
                                })
                            else:
                                # Full inline mode: OCR on the cropped vehicle region
                                # (not the whole frame) so the stutter is small.
                                plate = extract_plate_cropped(frame_bgr, v["bbox"], ocr)
                                sc, lv, act, rep = priority_score(
                                    v["type"], camera_id, plate or "", conn)
                                annotated_full = annotate(frame_bgr, [v])
                                evidence = generate_evidence(
                                    frame_bgr, annotated_full,
                                    v, plate, camera_id, private_key)
                                bxv = [int(c) for c in v["bbox"]]
                                vcrop = frame_bgr[max(0, bxv[1]):bxv[3],
                                                  max(0, bxv[0]):bxv[2]]
                                snap = save_snapshot(annotated_full, vcrop,
                                                     evidence["sha256_hash"])
                                save_violation(conn, evidence, sc, lv,
                                               camera_id, plate or "",
                                               snapshot_path=snap)
                                vgraph.add_violation(plate or "", v["type"],
                                                     camera_id, evidence["timestamp_unix"])
                                v_cat = classify_plate_category(vcrop)
                                evidence["vehicle_category"] = v_cat
                                serial = " 🚨SERIAL" if rep >= 7 else ("")
                                st.session_state.live_log.append({
                                    "Time":      datetime.now().strftime("%H:%M:%S"),
                                    "Track ID":  tid,
                                    "Violation": v["type"],
                                    "Conf":      f"{v['confidence']:.0%}",
                                    "Score":     sc,
                                    "Level":     lv + serial,
                                    "Action":    act,
                                    "Plate":     plate or "UNREADABLE",
                                    "Status":    "⏳ PENDING REVIEW",
                                })
                                st.session_state["last_evidence"] = evidence
                            new_confirmations.append(v)

                # ── Annotate and display current frame ─────────────────────
                # Draw ALL detected violations (not just confirmed) for visual clarity
                display_frame = annotate(frame_bgr, violations)

                # Overlay track IDs on each box
                if ids:
                    for box, tid in zip(boxes.xyxy.tolist(), ids):
                        x1, y1 = int(box[0]), int(box[1])
                        cv2.putText(display_frame, f"ID:{tid}",
                                    (x1, max(y1 - 20, 12)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.35,
                                    (255, 255, 0), 1, cv2.LINE_AA)

                frame_slot.image(
                    cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB),
                    use_container_width=True)
                counter_slot.caption(
                    f"Frame {frame_idx} | Processed {processed} | "
                    f"Confirmed violations: {len(st.session_state.confirmed_ids)}")

                # Update live log table
                if st.session_state.live_log:
                    log_slot.dataframe(
                        pd.DataFrame(st.session_state.live_log),
                        use_container_width=True, height=420)

                # ── Debug panel: raw helmet model outputs this frame ───────
                if debug_slot is not None:
                    hdbg = st.session_state.get("helmet_debug", [])
                    _bnames = track_results[0].names
                    n_bikes = sum(1 for b in track_results[0].boxes
                                  if _bnames[int(b.cls)] == "motorcycle")
                    if hdbg:
                        dbg_df = pd.DataFrame(hdbg)
                        debug_slot.dataframe(
                            dbg_df, use_container_width=True, height=160)
                    else:
                        debug_slot.caption(
                            f"🔬 Debug: {n_bikes} motorcycle(s) detected this "
                            f"frame, 0 rider crops classified "
                            f"(riders not matched to bikes, or crops too small).")

            cap.release()

            # ── Deferred evidence generation (smooth live mode) ────────────────
            if smooth_mode and st.session_state.pending_evidence:
                prog = st.progress(0.0, text="Generating signed evidence for "
                                              "confirmed violations…")
                total_pe = len(st.session_state.pending_evidence)
                for pe_idx, pe in enumerate(st.session_state.pending_evidence):
                    v = pe["violation"]
                    plate = _read_plate_from_img(pe["crop"], ocr) \
                        if pe["crop"].size else "UNREADABLE"
                    sc, lv, act, rep = priority_score(
                        v["type"], camera_id, plate or "", conn)
                    annotated_full = annotate(pe["frame"], [v])
                    evidence = generate_evidence(
                        pe["frame"], annotated_full,
                        v, plate, camera_id, private_key)
                    snap = save_snapshot(annotated_full, pe["crop"],
                                         evidence["sha256_hash"])
                    save_violation(conn, evidence, sc, lv, camera_id,
                                   plate or "", snapshot_path=snap)
                    vgraph.add_violation(plate or "", v["type"],
                                         camera_id, evidence["timestamp_unix"])
                    v_cat = classify_plate_category(pe["crop"])
                    evidence["vehicle_category"] = v_cat
                    st.session_state["last_evidence"] = evidence
                    # back-fill the live_log row for this track/type
                    for row in st.session_state.live_log:
                        if row["Track ID"] == pe["tid"] and row["Violation"] == v["type"]:
                            row["Plate"]  = plate or "UNREADABLE"
                            row["Score"]  = sc
                            row["Level"]  = lv + (" 🚨SERIAL" if rep >= 7 else "")
                            row["Action"] = act
                            break
                    prog.progress((pe_idx + 1) / total_pe,
                                  text=f"Signed evidence {pe_idx+1}/{total_pe}")
                prog.empty()
                st.session_state.pending_evidence = []

            st.success(
                f"Analysis complete — {processed} frames processed, "
                f"{len(st.session_state.confirmed_ids)} unique violations confirmed "
                f"(3-of-5 frame threshold).")

            if st.session_state.live_log:
                st.subheader("Full Session Violation Report")
                st.dataframe(
                    pd.DataFrame(st.session_state.live_log),
                    use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — Review Queue
# ─────────────────────────────────────────────────────────────────────────────
with tab2:
    st.markdown("""
    <div style="margin-bottom:1.8rem">
      <p style="font-size:0.62rem;font-weight:700;letter-spacing:0.18em;text-transform:uppercase;color:rgba(0,0,0,0.25);margin-bottom:4px">Human In The Loop</p>
      <h1 style="font-family:'Outfit',sans-serif;font-size:2.2rem;font-weight:700;letter-spacing:-0.03em;color:#111111;margin:0">Review Queue</h1>
      <p style="font-size:0.85rem;color:rgba(0,0,0,0.35);margin-top:4px">Verify and sign off on detected traffic violations to establish audit provenance.</p>
    </div>
    """, unsafe_allow_html=True)

    cur = conn.cursor()

    # ── search box ────────────────────────────────────────────────────────────
    search_term = st.text_input("Search by plate number or violation type",
                                placeholder="e.g. DL9S or Helmet Non-Compliance")
    if search_term:
        cur.execute("""
            SELECT id, datetime(timestamp,'unixepoch','localtime'),
                   plate_number, violation_type, confidence,
                   priority_score, priority_level, camera_id,
                   operator_action, snapshot_path
            FROM violations
            WHERE plate_number LIKE ? OR violation_type LIKE ?
            ORDER BY timestamp DESC LIMIT 50""",
            (f"%{search_term}%", f"%{search_term}%"))
        search_rows = cur.fetchall()
        if search_rows:
            st.dataframe(
                pd.DataFrame(search_rows, columns=[
                    "ID", "Time", "Plate", "Violation", "Conf",
                    "Score", "Level", "Camera", "Action", "Snapshot"]),
                use_container_width=True)
        else:
            st.info(f"No records matching '{search_term}'.")
        st.divider()

    # ── pending count banner ───────────────────────────────────────────────────
    cur.execute("SELECT COUNT(*) FROM violations WHERE operator_action IS NULL")
    pending_count = cur.fetchone()[0]

    if pending_count > 0:
        st.error(
            f"**{pending_count} violation(s) awaiting human review** — "
            "no enforcement action has been taken on these records. "
            "Confirm, dismiss, or escalate each one below.")
    else:
        st.success("All violations have been reviewed.")

    st.divider()

    # ── SECTION 1: Pending (operator_action IS NULL) ──────────────────────────
    st.subheader("Pending Review")
    st.caption("These have NOT been confirmed — no challan issued yet. Human decision required.")
    cur.execute("""
        SELECT id, datetime(timestamp,'unixepoch','localtime'),
               plate_number, violation_type, confidence,
               priority_score, priority_level, camera_id, snapshot_path
        FROM violations WHERE operator_action IS NULL
        ORDER BY priority_score DESC LIMIT 30""")
    pending_rows = cur.fetchall()

    if not pending_rows:
        st.info("No pending violations.")
    else:
        st.caption("Each card shows the exact saved frame. Look at the image, "
                   "then Confirm / Dismiss / Escalate. Nothing is enforced until you click.")

        for row in pending_rows:
            (vid, vtime, plate, vtype, vconf,
             vscore, vlevel, vcam, snap) = row

            badge = {"CRITICAL": "🔴", "HIGH": "🟠",
                     "MEDIUM": "🟡", "LOW": "🟢"}.get(vlevel, "⚪")
            header = (f"{badge} #{vid} · {vtype} · {vlevel} · "
                      f"conf {vconf:.0%} · {plate or 'UNREADABLE'} · {vtime}")

            with st.expander(header, expanded=False):
                img_col, info_col = st.columns([3, 2])

                with img_col:
                    full_img = snap
                    crop_img = (snap.replace("_full.jpg", "_crop.jpg")
                                if snap else None)
                    if full_img and os.path.exists(full_img):
                        st.image(full_img, caption="Evidence frame (exact moment)",
                                 use_container_width=True)
                        if crop_img and os.path.exists(crop_img):
                            st.image(crop_img, caption="Zoomed crop — cross-check the rider/plate",
                                     width=260)
                    else:
                        st.warning("No saved snapshot for this record "
                                   "(seeded sample or pre-snapshot run).")

                with info_col:
                    st.markdown(f"**Violation:** {vtype}")
                    st.markdown(f"**Confidence:** {vconf:.0%}")
                    st.markdown(f"**Priority:** {vscore} ({vlevel})")
                    st.markdown(f"**Plate (OCR):** `{plate or 'UNREADABLE'}`")
                    st.markdown(f"**Camera:** {vcam}")
                    # Plate-colour vehicle category from snapshot crop
                    if snap and os.path.exists(snap.replace("_full.jpg", "_crop.jpg")):
                        _crop_path = snap.replace("_full.jpg", "_crop.jpg")
                        _crop_bgr  = cv2.imread(_crop_path)
                        v_category = classify_plate_category(_crop_bgr) if _crop_bgr is not None else "Unknown"
                    else:
                        v_category = "Unknown"
                    st.markdown(f"**Vehicle Category:** {v_category}")
                    vahan = vahan_lookup(plate or "")
                    st.markdown(f"**Registered owner:** {vahan['owner']}")
                    st.markdown(f"**Vehicle:** {vahan['vehicle']}")

                    reason = st.selectbox(
                        "Dismissal reason (required to dismiss)",
                        ["—", "Poor image quality", "Wrong classification",
                         "No violation present", "Vehicle type error",
                         "Lighting / weather condition", "Other"],
                        key=f"reason_{vid}")

                    b1, b2, b3 = st.columns(3)
                    if b1.button("✅ Confirm", key=f"conf_{vid}", type="primary"):
                        conn.execute(
                            "UPDATE violations SET operator_action='CONFIRMED',"
                            "operator_timestamp=? WHERE id=?", (time.time(), vid))
                        conn.commit()
                        st.success(f"#{vid} confirmed — challan queued.")
                        st.rerun()
                    if b2.button("❌ Dismiss", key=f"dis_{vid}"):
                        if reason == "—":
                            st.warning("Pick a dismissal reason — it feeds active learning.")
                        else:
                            conn.execute(
                                "UPDATE violations SET operator_action='DISMISSED',"
                                "operator_timestamp=?,dismissal_reason=? WHERE id=?",
                                (time.time(), reason, vid))
                            conn.commit()
                            st.warning(f"#{vid} dismissed ({reason}) — logged for retraining.")
                            st.rerun()
                    if b3.button("⬆️ Escalate", key=f"esc_{vid}"):
                        conn.execute(
                            "UPDATE violations SET operator_action='ESCALATED',"
                            "operator_timestamp=? WHERE id=?", (time.time(), vid))
                        conn.commit()
                        st.info(f"#{vid} escalated to supervisor.")
                        st.rerun()

    st.divider()

    # ── SECTION 2: Already reviewed ───────────────────────────────────────────
    st.subheader("Reviewed Violations")
    cur.execute("""
        SELECT id, datetime(timestamp,'unixepoch','localtime'),
               plate_number, violation_type, confidence,
               priority_score, priority_level, camera_id,
               operator_action, dismissal_reason
        FROM violations WHERE operator_action IS NOT NULL
        ORDER BY operator_timestamp DESC LIMIT 30""")
    reviewed_rows = cur.fetchall()
    if reviewed_rows:
        df_r = pd.DataFrame(reviewed_rows, columns=[
            "ID", "Time", "Plate", "Violation", "Conf",
            "Priority", "Level", "Camera", "Decision", "Dismiss Reason"])
        df_r["Conf"] = df_r["Conf"].apply(lambda x: f"{x:.0%}")
        df_r["Decision"] = df_r["Decision"].map({
            "CONFIRMED": "✅ CONFIRMED",
            "DISMISSED": "❌ DISMISSED",
            "ESCALATED": "⬆️ ESCALATED"
        }).fillna(df_r["Decision"])
        st.dataframe(df_r, use_container_width=True)
    else:
        st.info("No reviewed violations yet.")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — Analytics
# ─────────────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown("""
    <div style="margin-bottom:1.8rem">
      <p style="font-size:0.62rem;font-weight:700;letter-spacing:0.18em;text-transform:uppercase;color:rgba(0,0,0,0.25);margin-bottom:4px">Analytics Dashboard</p>
      <h1 style="font-family:'Outfit',sans-serif;font-size:2.2rem;font-weight:700;letter-spacing:-0.03em;color:#111111;margin:0">System Performance</h1>
      <p style="font-size:0.85rem;color:rgba(0,0,0,0.35);margin-top:4px">Statistical analysis of traffic violations, hotspot distributions, and active learning calibration metrics.</p>
    </div>
    """, unsafe_allow_html=True)

    cur = conn.cursor()
    cur.execute("""
        SELECT violation_type, COUNT(*) as cnt
        FROM violations GROUP BY violation_type ORDER BY cnt DESC""")
    vtype_data = cur.fetchall()

    cur.execute("""
        SELECT camera_id, COUNT(*) as cnt
        FROM violations GROUP BY camera_id ORDER BY cnt DESC""")
    cam_data = cur.fetchall()

    col1, col2 = st.columns(2)

    if vtype_data:
        df_v = pd.DataFrame(vtype_data, columns=["Violation Type", "Count"])
        fig1 = px.bar(df_v, x="Count", y="Violation Type",
                      orientation="h", title="Violations by Type",
                      color="Count", color_continuous_scale="Reds")
        col1.plotly_chart(fig1, use_container_width=True)

    if cam_data:
        df_c = pd.DataFrame(cam_data, columns=["Location", "Count"])
        fig2 = px.pie(df_c, names="Location", values="Count",
                      title="Violations by Camera Location")
        col2.plotly_chart(fig2, use_container_width=True)

    # Bengaluru hotspot map
    st.subheader("Violation Hotspot Map — Bengaluru")
    hotspot_df = pd.DataFrame({
        "lat":       [12.9165, 12.9762, 13.0358, 12.9591, 12.9698],
        "lon":       [77.6229, 77.5772, 77.5970, 77.7081, 77.7499],
        "location":  ["Silk Board", "KR Circle", "Hebbal",
                      "Marathahalli", "Whitefield"],
        "violations":[cur.execute(
            "SELECT COUNT(*) FROM violations WHERE camera_id LIKE ?",
            (f"%{loc}%",)).fetchone()[0]
            for loc in ["silk_board","kr_circle","hebbal",
                        "marathahalli","whitefield"]],
    })
    hotspot_df["violations"] = hotspot_df["violations"].apply(lambda x: max(x, 1))
    fig3 = px.scatter_mapbox(
        hotspot_df, lat="lat", lon="lon",
        size="violations", hover_name="location",
        hover_data=["violations"],
        mapbox_style="open-street-map", zoom=11,
        title="Live Violation Heatmap — Bengaluru")
    st.plotly_chart(fig3, use_container_width=True)

    # Active learning stats
    st.subheader("Active Learning — False Positive Rate by Camera")
    cur.execute("""
        SELECT camera_id,
               COUNT(*) as total,
               SUM(CASE WHEN operator_action='DISMISSED' THEN 1 ELSE 0 END) as dismissed
        FROM violations WHERE operator_action IS NOT NULL
        GROUP BY camera_id""")
    al_data = cur.fetchall()
    if al_data:
        al_df = pd.DataFrame(al_data, columns=["Camera", "Total", "Dismissed"])
        al_df["FP Rate"] = (al_df["Dismissed"] / al_df["Total"] * 100).round(1)
        st.dataframe(al_df, use_container_width=True)
        high_fp = al_df[al_df["FP Rate"] > 15]
        for _, row in high_fp.iterrows():
            st.warning(f"{row['Camera']} has {row['FP Rate']}% FP rate — "
                       "recommend camera calibration review.")
    else:
        st.info("No operator actions recorded yet. "
                "Review violations in the Review Queue tab.")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — Knowledge Graph
# ─────────────────────────────────────────────────────────────────────────────
with tab4:
    st.markdown("""
    <div style="margin-bottom:1.8rem">
      <p style="font-size:0.62rem;font-weight:700;letter-spacing:0.18em;text-transform:uppercase;color:rgba(0,0,0,0.25);margin-bottom:4px">Graph Explorer</p>
      <h1 style="font-family:'Outfit',sans-serif;font-size:2.2rem;font-weight:700;letter-spacing:-0.03em;color:#111111;margin:0">Knowledge Graph</h1>
      <p style="font-size:0.85rem;color:rgba(0,0,0,0.35);margin-top:4px">Traverse junctions, vehicle plate nodes, and violation types using network analysis.</p>
    </div>
    """, unsafe_allow_html=True)
    backend_label = vgraph.backend
    st.caption(f"Nodes: vehicles, cameras, violation types. "
               f"Edges: recorded violations. **Backend: {backend_label}**")
    if "Neo4j" in backend_label:
        st.success("Connected to Neo4j graph database.")
    else:
        st.info("Running on SQLite (install Neo4j Desktop + `pip install neo4j` "
                "and restart to use the full graph backend).")

    # ── build graph data from DB ──────────────────────────────────────────────
    cur = conn.cursor()
    cur.execute("""
        SELECT plate_number, camera_id, violation_type, priority_score
        FROM violations ORDER BY timestamp DESC LIMIT 60""")
    rows = cur.fetchall()

    if rows:
        # Assign unique positions to node types
        plates   = list({r[0] for r in rows})
        cameras  = list({r[1] for r in rows})
        vtypes   = list({r[2] for r in rows})

        import math
        node_x, node_y, node_text, node_color, node_size = [], [], [], [], []

        def circle_pos(items, cx, cy, r):
            pts = []
            for i, item in enumerate(items):
                angle = 2 * math.pi * i / max(len(items), 1)
                pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
            return pts

        plate_pos  = circle_pos(plates,  0,    0,    2.5)
        camera_pos = circle_pos(cameras, 6,    0,    1.2)
        vtype_pos  = circle_pos(vtypes,  3,    4,    1.5)

        for i, p in enumerate(plates):
            node_x.append(plate_pos[i][0]); node_y.append(plate_pos[i][1])
            node_text.append(p); node_color.append("#e74c3c"); node_size.append(22)
        for i, c in enumerate(cameras):
            node_x.append(camera_pos[i][0]); node_y.append(camera_pos[i][1])
            node_text.append(c.replace("_", " ").title())
            node_color.append("#2980b9"); node_size.append(28)
        for i, v in enumerate(vtypes):
            node_x.append(vtype_pos[i][0]); node_y.append(vtype_pos[i][1])
            short = v.split()[0]
            node_text.append(short); node_color.append("#f39c12"); node_size.append(20)

        # build edge traces
        edge_x, edge_y = [], []
        plate_map  = {p: plate_pos[i]  for i, p in enumerate(plates)}
        camera_map = {c: camera_pos[i] for i, c in enumerate(cameras)}
        vtype_map  = {v: vtype_pos[i]  for i, v in enumerate(vtypes)}

        for plate, camera, vtype, _ in rows:
            px, py = plate_map[plate]
            cx, cy = camera_map[camera]
            vx, vy = vtype_map[vtype]
            # plate → camera
            edge_x += [px, cx, None]
            edge_y += [py, cy, None]
            # plate → vtype
            edge_x += [px, vx, None]
            edge_y += [py, vy, None]

        edge_trace = go.Scatter(
            x=edge_x, y=edge_y, mode="lines",
            line=dict(width=0.8, color="#555"),
            hoverinfo="none")

        node_trace = go.Scatter(
            x=node_x, y=node_y, mode="markers+text",
            text=node_text, textposition="top center",
            marker=dict(size=node_size, color=node_color,
                        line=dict(width=1.5, color="#222")),
            hoverinfo="text")

        fig_kg = go.Figure(
            data=[edge_trace, node_trace],
            layout=go.Layout(
                title="Vehicle → Camera → Violation Network",
                showlegend=False,
                margin=dict(l=20, r=20, t=50, b=20),
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                height=520,
                plot_bgcolor="#ffffff",
                paper_bgcolor="#ffffff",
                font=dict(color="#111111"),
            ))

        st.plotly_chart(fig_kg, use_container_width=True)

        # legend
        lc1, lc2, lc3 = st.columns(3)
        lc1.markdown("🔴 **Red nodes** = Vehicle plates")
        lc2.markdown("🔵 **Blue nodes** = Camera locations")
        lc3.markdown("🟡 **Yellow nodes** = Violation types")

    else:
        st.info("No violations in DB yet. Upload images in Live Detection to populate the graph.")

    st.divider()

    # ── Plate cloning check ───────────────────────────────────────────────────
    st.subheader("Plate Cloning Alert")
    clone_plate = st.text_input("Check plate for simultaneous multi-location sightings",
                                placeholder="e.g. DL9SC4567", key="clone_input")
    if clone_plate:
        sightings = vgraph.plate_cloning_check(
            clone_plate.upper(), "any_location", window_minutes=30)
        if sightings:
            st.error(f"ALERT: Plate {clone_plate} seen at multiple locations within 30 min — "
                     "possible plate cloning!")
            st.json(sightings)
        else:
            st.success(f"No cloning alert for {clone_plate} in last 30 minutes.")

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Repeat Offenders (30 days)")
        repeats = vgraph.repeat_offenders(min_count=2)
        if repeats:
            df_r = pd.DataFrame(repeats, columns=["Plate", "Violations", "Types"])
            df_r["Status"] = df_r["Violations"].apply(
                lambda x: "🔴 Refer to RTO" if x >= 7
                else ("🟠 Senior Officer" if x >= 3 else "🟡 Watch"))
            st.dataframe(df_r, use_container_width=True)
        else:
            st.info("No repeat offenders yet.")

    with col2:
        st.subheader("Camera Hotspot Ranking")
        hotspots = kg_hotspots(conn)
        if hotspots:
            df_h = pd.DataFrame(hotspots, columns=["Camera", "Violations", "Avg Priority"])
            df_h["Avg Priority"] = df_h["Avg Priority"].round(1)
            st.dataframe(df_h, use_container_width=True)
        else:
            st.info("No hotspot data yet.")

    st.divider()
    st.subheader("Plate Cloning Detection (Simulated)")
    st.info("Finds plates seen at 2 locations >5 km apart within 10 min — physically impossible.")
    clone_demo = pd.DataFrame({
        "Plate":      ["KA03ZZ7777"],
        "Location 1": ["Silk Board — 08:23"],
        "Location 2": ["Hebbal — 08:31"],
        "Distance":   ["14.2 km"],
        "Time Gap":   ["8 minutes"],
        "Status":     ["🚨 IMPOSSIBLE — cloned plate flagged"],
    })
    st.dataframe(clone_demo, use_container_width=True)

    st.divider()
    st.subheader("Infrastructure Failure Signature")
    st.markdown(
        "**Finding:** Wrong-side violations cluster at Silk Board 17:30–19:00 daily. "
        "MapMyIndia cross-check: no legal U-turn within 800m southbound.\n\n"
        "**BBMP Recommendation:** Add U-turn at Hosur Road km 4.2 — "
        "estimated **68% reduction** in wrong-side violations without extra enforcement.")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — Evidence Verification
# ─────────────────────────────────────────────────────────────────────────────
with tab5:
    st.markdown("""
    <div style="margin-bottom:1.8rem">
      <p style="font-size:0.62rem;font-weight:700;letter-spacing:0.18em;text-transform:uppercase;color:rgba(0,0,0,0.25);margin-bottom:4px">Evidence Verification</p>
      <h1 style="font-family:'Outfit',sans-serif;font-size:2.2rem;font-weight:700;letter-spacing:-0.03em;color:#111111;margin:0">Evidence Integrity</h1>
      <p style="font-size:0.85rem;color:rgba(0,0,0,0.35);margin-top:4px">Verify SHA-256 and RSA-PSS cryptographic signatures to validate chain-of-custody provenance.</p>
    </div>
    """, unsafe_allow_html=True)
    st.info(
        "Every evidence record is SHA-256 hashed and RSA-signed. "
        "Verify that a record has not been tampered with since generation. "
        "Production system uses an HSM/TPM chip — private key never exposed. "
        "Prototype uses a software key for demonstration.")

    if "last_evidence" in st.session_state:
        ev = st.session_state["last_evidence"]

        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("**Latest Evidence Record**")
            display = {k: v for k, v in ev.items()
                       if k not in {"annotated_image_b64",
                                    "original_image_b64"}}
            st.json(display)

        with col2:
            st.markdown("**Verification**")
            if st.button("🔐 Verify Integrity", type="primary"):
                ok, msg = verify_evidence(dict(ev), private_key)
                if ok:
                    st.success(f"✅ {msg}")
                    st.markdown(f"**SHA-256:** `{ev.get('sha256_hash','')}`")
                    st.markdown(f"**Blockchain anchor:** `{ev.get('blockchain_anchor','')}`")
                    st.markdown("**TPM status:** Software key (prototype) — "
                                "HSM/Infineon SLB9670 in production")
                else:
                    st.error(f"❌ {msg}")

            st.divider()
            st.markdown("**Tamper Simulation**")
            if st.button("⚠️ Simulate Tamper & Re-verify"):
                tampered = dict(ev)
                tampered["plate_number"] = "KA00AA0000"   # alter a field
                ok, msg = verify_evidence(tampered, private_key)
                st.error(f"Tampered record result: ❌ {msg}")
                st.caption("The hash breaks the moment any field changes. "
                           "This is what makes the evidence court-admissible.")
    else:
        st.info("Run a detection in the **Live Detection** tab first "
                "to generate an evidence record to verify here.")

    st.divider()
    st.subheader("Evidence Chain of Custody")
    st.markdown("""
| Layer | Prototype | Production |
|-------|-----------|------------|
| Hash | SHA-256 ✅ | SHA-256 ✅ |
| Signing | RSA software key ✅ | RSA + HSM/TPM chip |
| Key protection | File on disk | Infineon SLB9670 (tamper-erasure) |
| Timestamp | System clock | NTP + GPS satellite time |
| Blockchain anchor | Mock TX ID ✅ | Polygon network (real) |
| Transmission | Local SQLite | TLS 1.3 → BTP write-once DB |
| VAHAN lookup | Mock database ✅ | Live BTP API credentials |
    """)
