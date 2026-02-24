"""
Electrical Engineering Lab Grouping System
==========================================
Course Rep Tool for STUBTECH EE Department
- Student self-registration with validation
- Auto-grouping: 2 groups (Mechatronics) & 3 groups (Renewable Energy)
- Admin dashboard with PDF + Excel export (with Marks column)
- Full backup/restore system using JSON files
- Streamlit Cloud ready (no external database required)
"""

import streamlit as st
import pandas as pd
import json
import os
import re
import hashlib
import random
import shutil
import zipfile
import base64
from io import BytesIO
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# ─────────────────────────────────────────────
#  PAGE CONFIG  (must be first Streamlit call)
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="EE Lab Grouping System",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
#  GLOBAL STYLES
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600;700&display=swap');

/* ── Reset & Base ── */
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(160deg, #0f1923 0%, #1a2d42 100%);
    border-right: 1px solid #2a4060;
}
section[data-testid="stSidebar"] * { color: #c8d8e8 !important; }
section[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    color: #e0eaf4 !important;
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
    margin-bottom: 4px;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(56,189,248,0.15) !important;
    border-color: #38bdf8 !important;
    color: #38bdf8 !important;
}
section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #0ea5e9, #0284c7) !important;
    border: none !important;
    color: #fff !important;
    font-weight: 600 !important;
}

/* ── Main area ── */
.main .block-container { padding-top: 2rem; max-width: 1200px; }

/* ── Custom cards ── */
.ee-card {
    background: #ffffff;
    border: 1px solid #e5eaf0;
    border-radius: 14px;
    padding: 1.5rem 1.75rem;
    margin-bottom: 1.25rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}
.ee-card-dark {
    background: linear-gradient(135deg, #0f1923 0%, #1a2d42 100%);
    border: 1px solid #2a4060;
    border-radius: 14px;
    padding: 1.5rem 1.75rem;
    margin-bottom: 1.25rem;
    color: #c8d8e8;
}

/* ── Page title ── */
.page-title {
    font-family: 'Space Mono', monospace;
    font-size: 2rem;
    font-weight: 700;
    color: #0f1923;
    letter-spacing: -0.5px;
    margin-bottom: 0.25rem;
}
.page-subtitle {
    font-size: 1rem;
    color: #64748b;
    margin-bottom: 1.5rem;
    font-weight: 400;
}

/* ── Metric boxes ── */
.metric-box {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1.1rem 1.3rem;
    text-align: center;
}
.metric-box .metric-value {
    font-family: 'Space Mono', monospace;
    font-size: 2rem;
    font-weight: 700;
    color: #0ea5e9;
    line-height: 1;
}
.metric-box .metric-label {
    font-size: 0.78rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 0.4rem;
    font-weight: 600;
}

/* ── Group badges ── */
.group-badge-a {
    background: #dbeafe; color: #1e40af;
    padding: 2px 10px; border-radius: 20px;
    font-size: 0.78rem; font-weight: 700; letter-spacing: 0.04em;
}
.group-badge-b {
    background: #dcfce7; color: #166534;
    padding: 2px 10px; border-radius: 20px;
    font-size: 0.78rem; font-weight: 700; letter-spacing: 0.04em;
}
.group-badge-c {
    background: #fef9c3; color: #713f12;
    padding: 2px 10px; border-radius: 20px;
    font-size: 0.78rem; font-weight: 700; letter-spacing: 0.04em;
}

/* ── Buttons ── */
.stButton > button {
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    border-radius: 9px !important;
    transition: all 0.2s ease !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #0ea5e9, #0284c7) !important;
    border: none !important;
    color: #fff !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(14,165,233,0.35) !important;
}

/* ── Form inputs ── */
.stTextInput input, .stSelectbox select {
    border-radius: 8px !important;
    border: 1.5px solid #e2e8f0 !important;
    font-family: 'DM Sans', sans-serif !important;
}
.stTextInput input:focus {
    border-color: #0ea5e9 !important;
    box-shadow: 0 0 0 3px rgba(14,165,233,0.12) !important;
}

/* ── Success / Error ── */
.stAlert {
    border-radius: 10px !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab"] {
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
}

/* ── Divider ── */
.ee-divider {
    border: none;
    border-top: 1px solid #e5eaf0;
    margin: 1.5rem 0;
}

/* ── Hero banner ── */
.hero-banner {
    background: linear-gradient(135deg, #0f1923 0%, #0c4a6e 50%, #075985 100%);
    border-radius: 16px;
    padding: 2.5rem 2.5rem;
    margin-bottom: 2rem;
    position: relative;
    overflow: hidden;
}
.hero-banner::before {
    content: "⚡";
    position: absolute;
    right: 2rem;
    top: 50%;
    transform: translateY(-50%);
    font-size: 7rem;
    opacity: 0.08;
}
.hero-banner h1 {
    font-family: 'Space Mono', monospace !important;
    color: #f0f9ff !important;
    font-size: 1.8rem !important;
    margin: 0 0 0.5rem 0 !important;
    font-weight: 700 !important;
}
.hero-banner p {
    color: #7dd3fc !important;
    font-size: 0.95rem !important;
    margin: 0 !important;
    font-weight: 400 !important;
}

/* ── Admin info boxes ── */
.info-strip {
    background: #f0f9ff;
    border-left: 4px solid #0ea5e9;
    border-radius: 0 8px 8px 0;
    padding: 0.75rem 1rem;
    margin-bottom: 1rem;
    font-size: 0.9rem;
    color: #0c4a6e;
}

/* ── Table styling ── */
.dataframe { font-size: 0.88rem !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  CONSTANTS & PATHS
# ─────────────────────────────────────────────
_BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR    = os.path.join(_BASE, "ee_data")
BACKUP_DIR  = os.path.join(_BASE, "ee_backups")

STUDENTS_FILE    = os.path.join(DATA_DIR, "students.json")
MECH_FILE        = os.path.join(DATA_DIR, "mech_groups.json")
RENEW_FILE       = os.path.join(DATA_DIR, "renew_groups.json")
STATE_FILE       = os.path.join(DATA_DIR, "app_state.json")
LOG_FILE         = os.path.join(DATA_DIR, "activity_log.json")

ADMIN_USER = "admin"
ADMIN_HASH = hashlib.sha256("eelab2024".encode()).hexdigest()

# Minimum students required before grouping
MIN_STUDENTS = 3

# ─────────────────────────────────────────────
#  FILE / DATA UTILITIES
# ─────────────────────────────────────────────

def init_storage():
    """Create directories and seed empty data files."""
    os.makedirs(DATA_DIR,   exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    defaults = {
        STUDENTS_FILE: [],
        MECH_FILE:     {"Group A": [], "Group B": []},
        RENEW_FILE:    {"Group A": [], "Group B": [], "Group C": []},
        STATE_FILE:    {"last_backup": None, "last_grouping": None, "version": "1.0"},
        LOG_FILE:      [],
    }
    for path, default in defaults.items():
        if not os.path.exists(path):
            _write(path, default)


def _write(path: str, data) -> None:
    """Atomic JSON write via temp file."""
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def _read(path: str):
    """Read JSON file; return None on error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def log_event(event: str, detail: dict = None):
    """Append an event to the activity log (silent on failure)."""
    try:
        logs = _read(LOG_FILE) or []
        logs.append({
            "event":     event,
            "detail":    detail or {},
            "timestamp": datetime.now().isoformat(),
        })
        if len(logs) > 2000:
            logs = logs[-2000:]
        _write(LOG_FILE, logs)
    except Exception:
        pass


# ─────────────────────────────────────────────
#  VALIDATION
# ─────────────────────────────────────────────

def validate_index(raw: str) -> Tuple[bool, str]:
    """Returns (ok, cleaned_or_error)."""
    cleaned = raw.strip().upper()
    if re.match(r"^STUBTECH\d{6}$", cleaned):
        return True, cleaned
    return False, "Index must be in the format STUBTECH followed by exactly 6 digits (e.g. STUBTECH220457)"


def validate_name(raw: str) -> Tuple[bool, str]:
    cleaned = " ".join(raw.strip().split())
    if len(cleaned) < 2:
        return False, "Name is too short"
    if not re.match(r"^[A-Za-z][A-Za-z .'\-]{1,}$", cleaned):
        return False, "Name should contain only letters, spaces, hyphens, or apostrophes"
    return True, cleaned


def check_duplicate(index: str, name: str) -> Tuple[bool, str]:
    students = _read(STUDENTS_FILE) or []
    idx_set  = {s["index"] for s in students}
    name_set = {s["name"].lower() for s in students}
    if index in idx_set:
        return True, f"Index **{index}** is already registered."
    if name.lower() in name_set:
        return True, f"A student named **{name}** is already registered."
    return False, ""


# ─────────────────────────────────────────────
#  GROUPING ENGINE
# ─────────────────────────────────────────────

def _build_mech_groups(students: List[dict]) -> Dict[str, list]:
    pool = random.sample(students, len(students))
    half = len(pool) // 2
    rem  = len(pool) % 2

    def entry(s, letter):
        return {**s, "group": f"Group {letter}", "lab": "Mechatronics Lab", "marks": ""}

    return {
        "Group A": [entry(s, "A") for s in pool[:half + rem]],
        "Group B": [entry(s, "B") for s in pool[half + rem:]],
    }


def _build_renew_groups(students: List[dict]) -> Dict[str, list]:
    pool  = random.sample(students, len(students))
    n     = len(pool)
    base  = n // 3
    extra = n % 3          # 0, 1, or 2
    sizes = [base + (1 if i < extra else 0) for i in range(3)]

    def entry(s, letter):
        return {**s, "group": f"Group {letter}", "lab": "Renewable Energy Systems Lab", "marks": ""}

    idx = 0
    groups = {}
    for letter, size in zip(["A", "B", "C"], sizes):
        groups[f"Group {letter}"] = [entry(s, letter) for s in pool[idx:idx + size]]
        idx += size
    return groups


def run_grouping() -> Tuple[bool, str]:
    students = _read(STUDENTS_FILE) or []
    if len(students) < MIN_STUDENTS:
        return False, f"Need at least {MIN_STUDENTS} students to form groups (currently {len(students)})."

    _write(MECH_FILE,  _build_mech_groups(students))
    _write(RENEW_FILE, _build_renew_groups(students))

    state = _read(STATE_FILE) or {}
    state["last_grouping"] = datetime.now().strftime("%d %b %Y, %H:%M")
    _write(STATE_FILE, state)

    log_event("groups_generated", {"total": len(students)})
    return True, f"Groups generated for {len(students)} students."


# ─────────────────────────────────────────────
#  BACKUP SYSTEM
# ─────────────────────────────────────────────

def create_backup() -> Tuple[str, bytes]:
    """Returns (label, zip_bytes)."""
    label = datetime.now().strftime("backup_%Y%m%d_%H%M%S")
    buf   = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in os.listdir(DATA_DIR):
            if fname.endswith(".json"):
                zf.write(os.path.join(DATA_DIR, fname), fname)
    raw = buf.getvalue()

    # Persist to disk as well
    zip_path = os.path.join(BACKUP_DIR, label + ".zip")
    with open(zip_path, "wb") as f:
        f.write(raw)

    state = _read(STATE_FILE) or {}
    state["last_backup"] = datetime.now().strftime("%d %b %Y, %H:%M")
    _write(STATE_FILE, state)

    log_event("backup_created", {"label": label})
    return label, raw


def list_backups() -> List[Dict]:
    if not os.path.exists(BACKUP_DIR):
        return []
    items = []
    for fname in sorted(os.listdir(BACKUP_DIR), reverse=True):
        if fname.endswith(".zip"):
            fp = os.path.join(BACKUP_DIR, fname)
            items.append({
                "name": fname,
                "path": fp,
                "size_kb": round(os.path.getsize(fp) / 1024, 1),
                "label": fname.replace("backup_", "").replace(".zip", "").replace("_", " "),
            })
    return items


def restore_backup(zip_bytes: bytes) -> Tuple[bool, str]:
    """Restore data files from uploaded zip bytes."""
    try:
        with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
            names = zf.namelist()
            if not any(n.endswith(".json") for n in names):
                return False, "No JSON files found in the uploaded backup."
            for name in names:
                if name.endswith(".json"):
                    dest = os.path.join(DATA_DIR, name)
                    with zf.open(name) as src, open(dest, "wb") as dst:
                        dst.write(src.read())
        log_event("backup_restored", {"files": names})
        return True, f"Restored {len(names)} files successfully."
    except Exception as e:
        return False, f"Restore failed: {e}"


# ─────────────────────────────────────────────
#  EXPORT: EXCEL
# ─────────────────────────────────────────────

def _df_from_groups(groups: Dict[str, list]) -> pd.DataFrame:
    rows = []
    for members in groups.values():
        for m in members:
            rows.append({
                "Index Number": m.get("index", ""),
                "Full Name":    m.get("name", ""),
                "Group":        m.get("group", ""),
                "Lab":          m.get("lab", ""),
                "Marks":        m.get("marks", ""),
            })
    return pd.DataFrame(rows)


def export_excel_single(groups: Dict[str, list], lab_name: str) -> bytes:
    """One sheet per group, with a Marks column."""
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for group_name, members in groups.items():
            df = pd.DataFrame([{
                "No.":          i + 1,
                "Index Number": m["index"],
                "Full Name":    m["name"],
                "Marks":        m.get("marks", ""),
            } for i, m in enumerate(members)])
            safe_sheet = f"{group_name}"
            df.to_excel(writer, sheet_name=safe_sheet, index=False)

            ws = writer.sheets[safe_sheet]
            # Column widths
            for col in ws.columns:
                max_w = max((len(str(c.value or "")) for c in col), default=10)
                ws.column_dimensions[col[0].column_letter].width = min(max_w + 4, 50)

        # Summary sheet
        summary_df = _df_from_groups(groups)
        summary_df.to_excel(writer, sheet_name="All Groups", index=False)

    return buf.getvalue()


def export_excel_all(mech: Dict, renew: Dict) -> bytes:
    """All groups across both labs in one Excel workbook."""
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        # Mechatronics sheets
        for group_name, members in mech.items():
            df = pd.DataFrame([{
                "No.":          i + 1,
                "Index Number": m["index"],
                "Full Name":    m["name"],
                "Marks":        m.get("marks", ""),
            } for i, m in enumerate(members)])
            sheet = f"Mech {group_name}"
            df.to_excel(writer, sheet_name=sheet, index=False)
            ws = writer.sheets[sheet]
            for col in ws.columns:
                w = max((len(str(c.value or "")) for c in col), default=10)
                ws.column_dimensions[col[0].column_letter].width = min(w + 4, 45)

        # Renewable sheets
        for group_name, members in renew.items():
            df = pd.DataFrame([{
                "No.":          i + 1,
                "Index Number": m["index"],
                "Full Name":    m["name"],
                "Marks":        m.get("marks", ""),
            } for i, m in enumerate(members)])
            sheet = f"Renew {group_name}"
            df.to_excel(writer, sheet_name=sheet, index=False)
            ws = writer.sheets[sheet]
            for col in ws.columns:
                w = max((len(str(c.value or "")) for c in col), default=10)
                ws.column_dimensions[col[0].column_letter].width = min(w + 4, 45)

        # Master summary
        all_df = pd.concat([_df_from_groups(mech), _df_from_groups(renew)], ignore_index=True)
        all_df.to_excel(writer, sheet_name="Master List", index=False)

    return buf.getvalue()


# ─────────────────────────────────────────────
#  EXPORT: PDF  (pure Python via reportlab)
# ─────────────────────────────────────────────

def export_pdf(groups: Dict[str, list], lab_title: str) -> bytes:
    """
    Generate a formatted, printable PDF for one lab's groups.

    Fixes applied vs original:
      - Imports moved to module level (no lazy import / ImportError swallowing)
      - buf.getvalue() used instead of buf.seek(0)+buf.read() — getvalue() always
        returns the full buffer contents regardless of the internal pointer position
      - Empty-group guard: a header-only table is shown when a group has no members
        so doc.build() never receives a zero-row Table (which can crash ReportLab)
      - Removed the b'%PDF stub' fallback that produced a 29-byte non-PDF file
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph,
        Spacer, HRFlowable,
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    buf  = BytesIO()
    doc  = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=2*cm, bottomMargin=2*cm,
        leftMargin=2*cm, rightMargin=2*cm,
    )

    styles = getSampleStyleSheet()
    NAVY   = colors.HexColor("#0f1923")
    SKY    = colors.HexColor("#0ea5e9")
    STRIPE = colors.HexColor("#f8fafc")

    title_style = ParagraphStyle(
        "EETitle", parent=styles["Heading1"],
        fontSize=18, textColor=NAVY, spaceAfter=4,
        fontName="Helvetica-Bold", alignment=TA_CENTER,
    )
    sub_style = ParagraphStyle(
        "EESub", parent=styles["Normal"],
        fontSize=10, textColor=SKY, spaceAfter=6,
        fontName="Helvetica", alignment=TA_CENTER,
    )
    group_style = ParagraphStyle(
        "EEGroup", parent=styles["Heading2"],
        fontSize=13, textColor=NAVY, spaceAfter=4,
        fontName="Helvetica-Bold", spaceBefore=16,
    )
    footer_style = ParagraphStyle(
        "EEFooter", parent=styles["Normal"],
        fontSize=8, textColor=colors.grey,
        alignment=TA_CENTER,
    )

    story = []

    # ── Page header ──
    story.append(Paragraph("STUBTECH — Electrical Engineering Department", sub_style))
    story.append(Paragraph(lab_title, title_style))
    story.append(Paragraph(
        f"Lab Groupings  ·  Generated: {datetime.now().strftime('%d %B %Y, %H:%M')}",
        sub_style,
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=SKY, spaceAfter=12))

    # ── One table per group ──
    for group_name, members in groups.items():
        story.append(Paragraph(f"● {group_name}", group_style))

        # Always include the header row; add a "No students" notice when empty
        table_data = [["No.", "Index Number", "Full Name", "Marks / 100"]]
        if members:
            for i, m in enumerate(members, 1):
                table_data.append([
                    str(i),
                    m.get("index", ""),
                    m.get("name", ""),
                    str(m.get("marks", "") or ""),
                ])
        else:
            table_data.append(["—", "—", "No students assigned to this group", "—"])

        col_widths = [1.2*cm, 5*cm, 8.5*cm, 3*cm]
        t = Table(table_data, colWidths=col_widths, repeatRows=1)

        # Zebra-stripe body rows
        row_bg = [
            ("BACKGROUND", (0, r), (-1, r), STRIPE)
            for r in range(2, len(table_data), 2)
        ]

        t.setStyle(TableStyle([
            # Header row
            ("BACKGROUND",    (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, 0), 10),
            ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
            ("TOPPADDING",    (0, 0), (-1, 0), 8),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            # Body rows
            ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE",      (0, 1), (-1, -1), 9),
            ("ALIGN",         (0, 1), (1, -1),  "CENTER"),
            ("ALIGN",         (2, 1), (2, -1),  "LEFT"),
            ("ALIGN",         (3, 1), (3, -1),  "CENTER"),
            ("TOPPADDING",    (0, 1), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
            # Borders
            ("GRID",          (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("LINEBELOW",     (0, 0), (-1, 0),  1.5, SKY),
            *row_bg,
        ]))

        story.append(t)
        story.append(Spacer(1, 0.3*cm))

    # ── Footer ──
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        f"Total students: {sum(len(m) for m in groups.values())}  "
        f"·  Groups: {len(groups)}  "
        f"·  EE Lab Grouping System v1.0",
        footer_style,
    ))

    doc.build(story)

    # ── FIX: getvalue() returns the complete buffer regardless of pointer position ──
    return buf.getvalue()


# ─────────────────────────────────────────────
#  AUTHENTICATION
# ─────────────────────────────────────────────

def admin_login_ui():
    st.markdown('<div class="page-title">Admin Login</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Enter your credentials to access the admin dashboard</div>',
                unsafe_allow_html=True)

    with st.form("admin_login"):
        username = st.text_input("Username", placeholder="admin")
        password = st.text_input("Password", type="password", placeholder="••••••••")
        submitted = st.form_submit_button("🔐 Login", use_container_width=True, type="primary")

    if submitted:
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        if username == ADMIN_USER and pw_hash == ADMIN_HASH:
            st.session_state["admin_auth"] = True
            log_event("admin_login", {"user": username})
            st.rerun()
        else:
            st.error("❌ Invalid username or password. Default credentials: admin / eelab2024")
            log_event("admin_login_failed", {"user": username})

    st.markdown("""
    <div class="info-strip" style="margin-top:1rem;">
        ℹ️ Default credentials → <strong>Username:</strong> admin &nbsp;|&nbsp; <strong>Password:</strong> eelab2024
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  STUDENT REGISTRATION PAGE
# ─────────────────────────────────────────────

def student_page():
    # Hero banner
    st.markdown("""
    <div class="hero-banner">
        <h1>⚡ EE Lab Grouping System</h1>
        <p>STUBTECH Electrical Engineering Department — Register below to be assigned to your lab groups</p>
    </div>
    """, unsafe_allow_html=True)

    col_form, col_info = st.columns([3, 2], gap="large")

    with col_form:
        st.markdown('<div class="ee-card">', unsafe_allow_html=True)
        st.markdown("### 📝 Student Registration")
        st.markdown("Fill in your details to register for lab assignments.")

        with st.form("student_reg", clear_on_submit=True):
            name_input  = st.text_input("Full Name",     placeholder="e.g. Kwame Asante Mensah")
            index_input = st.text_input("Index Number",  placeholder="e.g. STUBTECH220457")
            submitted   = st.form_submit_button("✅ Register", use_container_width=True, type="primary")
        st.markdown('</div>', unsafe_allow_html=True)

        # Handle submission OUTSIDE form to avoid Streamlit nesting issues
        if submitted:
            errors = []

            ok_name, name_result = validate_name(name_input)
            if not ok_name:
                errors.append(f"**Name:** {name_result}")

            ok_idx, idx_result = validate_index(index_input)
            if not ok_idx:
                errors.append(f"**Index:** {idx_result}")

            if errors:
                for e in errors:
                    st.error(e)
            else:
                is_dup, dup_msg = check_duplicate(idx_result, name_result)
                if is_dup:
                    st.error(f"❌ {dup_msg}")
                else:
                    students = _read(STUDENTS_FILE) or []
                    students.append({
                        "name":  name_result,
                        "index": idx_result,
                        "registered_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })
                    _write(STUDENTS_FILE, students)

                    # Auto-regroup whenever a new student joins
                    if len(students) >= MIN_STUDENTS:
                        run_grouping()

                    log_event("student_registered", {"index": idx_result, "total": len(students)})
                    st.success(f"🎉 Welcome, **{name_result}**! You've been registered successfully.")
                    st.balloons()
                    st.rerun()

    with col_info:
        students = _read(STUDENTS_FILE) or []
        mech     = _read(MECH_FILE)  or {}
        renew    = _read(RENEW_FILE) or {}
        state    = _read(STATE_FILE) or {}

        # Stats
        st.markdown('<div class="ee-card">', unsafe_allow_html=True)
        st.markdown("### 📊 Current Stats")

        cols = st.columns(2)
        with cols[0]:
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-value">{len(students)}</div>
                <div class="metric-label">Registered</div>
            </div>""", unsafe_allow_html=True)
        with cols[1]:
            n_groups = len([g for g in mech.values() if g]) + len([g for g in renew.values() if g])
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-value">{n_groups}</div>
                <div class="metric-label">Active Groups</div>
            </div>""", unsafe_allow_html=True)

        if state.get("last_grouping"):
            st.markdown(f"<br>🕐 Last grouped: **{state['last_grouping']}**", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Group preview
        if students and mech:
            st.markdown('<div class="ee-card">', unsafe_allow_html=True)
            st.markdown("### 🔍 Your Group")
            st.markdown("Enter your index number to look up your assigned groups:")
            lookup = st.text_input("Index Number", placeholder="STUBTECH220457", key="lookup_idx")
            if lookup:
                ok, clean = validate_index(lookup)
                if ok:
                    found_mech  = next((m["group"] for g in mech.values()  for m in g if m["index"] == clean), None)
                    found_renew = next((m["group"] for g in renew.values() for m in g if m["index"] == clean), None)
                    if found_mech or found_renew:
                        if found_mech:
                            badge = "group-badge-a" if "A" in found_mech else "group-badge-b"
                            st.markdown(f"🔧 **Mechatronics Lab:** <span class='{badge}'>{found_mech}</span>", unsafe_allow_html=True)
                        if found_renew:
                            ltr = found_renew[-1]
                            badge = {"A": "group-badge-a", "B": "group-badge-b", "C": "group-badge-c"}.get(ltr, "group-badge-a")
                            st.markdown(f"🌱 **Renewable Energy Lab:** <span class='{badge}'>{found_renew}</span>", unsafe_allow_html=True)
                    else:
                        st.info("Index not found in current groups.")
                else:
                    st.warning("Please enter a valid index number.")
            st.markdown('</div>', unsafe_allow_html=True)

        # Recent registrations
        if students:
            st.markdown('<div class="ee-card">', unsafe_allow_html=True)
            st.markdown("### 🕐 Recent Registrations")
            for s in reversed(students[-5:]):
                st.markdown(f"• **{s['name']}** `{s['index']}`")
            st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  ADMIN DASHBOARD
# ─────────────────────────────────────────────

def admin_page():
    students = _read(STUDENTS_FILE) or []
    mech     = _read(MECH_FILE)  or {}
    renew    = _read(RENEW_FILE) or {}
    state    = _read(STATE_FILE) or {}
    logs     = _read(LOG_FILE)   or []

    # ── Sidebar admin nav ──
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🛠 Admin Panel")
    section = st.sidebar.radio(
        "Navigate to",
        ["📊 Dashboard", "👥 Groups", "📤 Export & Reports", "💾 Backup & Restore",
         "👤 Student List", "📋 Activity Log"],
        label_visibility="collapsed",
    )

    if st.sidebar.button("🚪 Logout", use_container_width=True):
        st.session_state["admin_auth"] = False
        st.rerun()

    # ─── DASHBOARD ───────────────────────────────────────────────
    if section == "📊 Dashboard":
        st.markdown('<div class="page-title">📊 Dashboard</div>', unsafe_allow_html=True)
        st.markdown('<div class="page-subtitle">Overview of lab registrations and groupings</div>',
                    unsafe_allow_html=True)

        total_mech  = sum(len(v) for v in mech.values())
        total_renew = sum(len(v) for v in renew.values())

        c1, c2, c3, c4, c5 = st.columns(5)
        for col, val, label in [
            (c1, len(students),               "Total Students"),
            (c2, total_mech,                  "Mech. Students"),
            (c3, total_renew,                 "Renew. Students"),
            (c4, state.get("last_backup") or "—", "Last Backup"),
            (c5, state.get("last_grouping") or "—", "Last Grouped"),
        ]:
            with col:
                st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-value" style="font-size:1.5rem">{val}</div>
                    <div class="metric-label">{label}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown("<hr class='ee-divider'>", unsafe_allow_html=True)

        col_mech, col_renew = st.columns(2)

        with col_mech:
            st.markdown("#### 🔧 Mechatronics Lab")
            for gname, members in mech.items():
                badge = "group-badge-a" if "A" in gname else "group-badge-b"
                st.markdown(f"<span class='{badge}'>{gname}</span> — **{len(members)} students**",
                            unsafe_allow_html=True)

        with col_renew:
            st.markdown("#### 🌱 Renewable Energy Systems Lab")
            for gname, members in renew.items():
                ltr   = gname[-1]
                badge = {"A": "group-badge-a", "B": "group-badge-b", "C": "group-badge-c"}.get(ltr, "group-badge-a")
                st.markdown(f"<span class='{badge}'>{gname}</span> — **{len(members)} students**",
                            unsafe_allow_html=True)

        st.markdown("<hr class='ee-divider'>", unsafe_allow_html=True)
        st.markdown("#### ⚡ Quick Actions")
        qa1, qa2, qa3 = st.columns(3)

        with qa1:
            if st.button("🔄 Re-generate Groups", use_container_width=True, type="primary"):
                ok, msg = run_grouping()
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.warning(msg)

        with qa2:
            if st.button("💾 Create Backup Now", use_container_width=True):
                label, raw = create_backup()
                st.success(f"Backup **{label}** created!")
                st.download_button(
                    "📥 Download Backup",
                    data=raw,
                    file_name=f"{label}.zip",
                    mime="application/zip",
                    key="quick_backup_dl"
                )

        with qa3:
            if st.button("📤 Export All (Excel)", use_container_width=True):
                xl = export_excel_all(mech, renew)
                st.download_button(
                    "📥 Download All Groups Excel",
                    data=xl,
                    file_name=f"EE_All_Groups_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="quick_all_excel"
                )

    # ─── GROUPS ──────────────────────────────────────────────────
    elif section == "👥 Groups":
        st.markdown('<div class="page-title">👥 Lab Groups</div>', unsafe_allow_html=True)

        if not students:
            st.info("No students registered yet.")
            return

        tab_mech, tab_renew = st.tabs(["🔧 Mechatronics Lab", "🌱 Renewable Energy Systems Lab"])

        with tab_mech:
            st.markdown(f"**{sum(len(v) for v in mech.values())} students** across 2 groups")
            cols = st.columns(2)
            for i, (gname, members) in enumerate(mech.items()):
                with cols[i]:
                    badge = "group-badge-a" if "A" in gname else "group-badge-b"
                    st.markdown(f"<span class='{badge}'>{gname}</span> &nbsp; ({len(members)} students)",
                                unsafe_allow_html=True)
                    if members:
                        df = pd.DataFrame([{
                            "#": j+1, "Index": m["index"], "Name": m["name"]
                        } for j, m in enumerate(members)])
                        st.dataframe(df, use_container_width=True, hide_index=True, height=300)
                    else:
                        st.info("Empty group")

        with tab_renew:
            st.markdown(f"**{sum(len(v) for v in renew.values())} students** across 3 groups")
            cols = st.columns(3)
            badge_map = {"A": "group-badge-a", "B": "group-badge-b", "C": "group-badge-c"}
            for i, (gname, members) in enumerate(renew.items()):
                with cols[i]:
                    ltr   = gname[-1]
                    badge = badge_map.get(ltr, "group-badge-a")
                    st.markdown(f"<span class='{badge}'>{gname}</span> &nbsp; ({len(members)} students)",
                                unsafe_allow_html=True)
                    if members:
                        df = pd.DataFrame([{
                            "#": j+1, "Index": m["index"], "Name": m["name"]
                        } for j, m in enumerate(members)])
                        st.dataframe(df, use_container_width=True, hide_index=True, height=300)
                    else:
                        st.info("Empty group")

        st.markdown("<hr class='ee-divider'>", unsafe_allow_html=True)
        if st.button("🔄 Re-generate All Groups", type="primary"):
            ok, msg = run_grouping()
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.warning(msg)

    # ─── EXPORT & REPORTS ────────────────────────────────────────
    elif section == "📤 Export & Reports":
        st.markdown('<div class="page-title">📤 Export & Reports</div>', unsafe_allow_html=True)
        st.markdown('<div class="page-subtitle">Download group lists with a Marks column for lecturers</div>',
                    unsafe_allow_html=True)

        if not students:
            st.info("No students registered yet.")
            return

        tab_mech_ex, tab_renew_ex, tab_all_ex = st.tabs([
            "🔧 Mechatronics Lab", "🌱 Renewable Energy Lab", "📦 All Groups"
        ])

        with tab_mech_ex:
            st.markdown("### Mechatronics Lab Export")
            st.markdown(f"Groups: **A** ({len(mech.get('Group A',[]))} students), "
                        f"**B** ({len(mech.get('Group B',[]))} students)")
            st.markdown("""
            <div class="info-strip">
                Both formats include a <strong>Marks / 100</strong> column so lecturers
                can attach scores directly to the printout.
            </div>
            """, unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                xl_mech = export_excel_single(mech, "Mechatronics Lab")
                st.download_button(
                    "📊 Download Excel (Mechatronics)",
                    data=xl_mech,
                    file_name=f"Mechatronics_Groups_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            with c2:
                pdf_mech = export_pdf(mech, "Mechatronics Lab")
                st.download_button(
                    "📄 Download PDF (Mechatronics)",
                    data=pdf_mech,
                    file_name=f"Mechatronics_Groups_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

            st.markdown("<hr class='ee-divider'>", unsafe_allow_html=True)
            st.markdown("**Preview**")
            for gname, members in mech.items():
                badge = "group-badge-a" if "A" in gname else "group-badge-b"
                st.markdown(f"<span class='{badge}'>{gname}</span>", unsafe_allow_html=True)
                if members:
                    df = pd.DataFrame([{
                        "No.": i+1, "Index Number": m["index"],
                        "Full Name": m["name"], "Marks": ""
                    } for i, m in enumerate(members)])
                    st.dataframe(df, use_container_width=True, hide_index=True)

        with tab_renew_ex:
            st.markdown("### Renewable Energy Systems Lab Export")
            st.markdown(
                f"Groups: **A** ({len(renew.get('Group A',[]))} students), "
                f"**B** ({len(renew.get('Group B',[]))} students), "
                f"**C** ({len(renew.get('Group C',[]))} students)"
            )
            st.markdown("""
            <div class="info-strip">
                Both formats include a <strong>Marks / 100</strong> column so lecturers
                can attach scores directly to the printout.
            </div>
            """, unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                xl_renew = export_excel_single(renew, "Renewable Energy Systems Lab")
                st.download_button(
                    "📊 Download Excel (Renewable Energy)",
                    data=xl_renew,
                    file_name=f"Renewable_Groups_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            with c2:
                pdf_renew = export_pdf(renew, "Renewable Energy Systems Lab")
                st.download_button(
                    "📄 Download PDF (Renewable Energy)",
                    data=pdf_renew,
                    file_name=f"Renewable_Groups_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

            st.markdown("<hr class='ee-divider'>", unsafe_allow_html=True)
            st.markdown("**Preview**")
            badge_map = {"A": "group-badge-a", "B": "group-badge-b", "C": "group-badge-c"}
            for gname, members in renew.items():
                badge = badge_map.get(gname[-1], "group-badge-a")
                st.markdown(f"<span class='{badge}'>{gname}</span>", unsafe_allow_html=True)
                if members:
                    df = pd.DataFrame([{
                        "No.": i+1, "Index Number": m["index"],
                        "Full Name": m["name"], "Marks": ""
                    } for i, m in enumerate(members)])
                    st.dataframe(df, use_container_width=True, hide_index=True)

        with tab_all_ex:
            st.markdown("### Complete Export — All Labs & Groups")
            xl_all = export_excel_all(mech, renew)
            st.download_button(
                "📦 Download Combined Excel (All Groups)",
                data=xl_all,
                file_name=f"EE_All_Lab_Groups_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary",
            )
            st.markdown("This workbook contains separate sheets for every group across both labs, plus a Master List.")

    # ─── BACKUP & RESTORE ────────────────────────────────────────
    elif section == "💾 Backup & Restore":
        st.markdown('<div class="page-title">💾 Backup & Restore</div>', unsafe_allow_html=True)
        st.markdown('<div class="page-subtitle">Protect your data — create, download, or restore backups</div>',
                    unsafe_allow_html=True)

        tab_create, tab_restore, tab_list = st.tabs(["➕ Create Backup", "🔄 Restore Backup", "📂 Backup History"])

        with tab_create:
            st.markdown("#### Create a New Backup")
            st.markdown("""
            A backup is a `.zip` archive of all JSON data files.
            Download and keep a copy somewhere safe (e.g. Google Drive, email).
            """)
            if st.button("💾 Create & Download Backup Now", type="primary", use_container_width=True):
                label, raw = create_backup()
                st.success(f"✅ Backup **{label}** created.")
                st.download_button(
                    "📥 Click to Download Backup",
                    data=raw,
                    file_name=f"{label}.zip",
                    mime="application/zip",
                    use_container_width=True,
                )

            st.markdown("<hr class='ee-divider'>", unsafe_allow_html=True)
            st.markdown("#### ⚠️ Danger Zone — Clear All Data")
            confirm_clear = st.checkbox("I understand this will permanently delete ALL student data")
            if confirm_clear:
                if st.button("🗑️ Delete All Students & Groups", type="secondary"):
                    # Auto-backup before clearing
                    create_backup()
                    _write(STUDENTS_FILE, [])
                    _write(MECH_FILE,  {"Group A": [], "Group B": []})
                    _write(RENEW_FILE, {"Group A": [], "Group B": [], "Group C": []})
                    log_event("data_cleared", {})
                    st.success("All data cleared. An automatic backup was saved first.")
                    st.rerun()

        with tab_restore:
            st.markdown("#### Restore from a Backup File")
            st.markdown("""
            <div class="info-strip">
                Upload a <code>.zip</code> backup file previously downloaded from this system.
                This will <strong>overwrite</strong> all current data.
            </div>
            """, unsafe_allow_html=True)

            uploaded = st.file_uploader("Upload Backup ZIP", type=["zip"])
            if uploaded:
                confirm_restore = st.checkbox("I understand this will overwrite current data")
                if confirm_restore:
                    if st.button("🔄 Restore Now", type="primary"):
                        # Auto-backup current state first
                        create_backup()
                        ok, msg = restore_backup(uploaded.read())
                        if ok:
                            st.success(f"✅ {msg} (Your previous data was auto-backed up first.)")
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")

            st.markdown("<hr class='ee-divider'>", unsafe_allow_html=True)
            st.markdown("#### Restore from Saved Backups on Server")
            server_backups = list_backups()
            if server_backups:
                opts = [b["name"] for b in server_backups]
                sel  = st.selectbox("Select a server backup", opts)
                sel_backup = next(b for b in server_backups if b["name"] == sel)
                st.caption(f"Size: {sel_backup['size_kb']} KB  •  {sel_backup['label']}")

                confirm_srv = st.checkbox("Confirm restore from server backup", key="confirm_srv")
                if confirm_srv:
                    if st.button("🔄 Restore Selected", type="secondary"):
                        create_backup()  # auto-backup first
                        with open(sel_backup["path"], "rb") as f:
                            ok, msg = restore_backup(f.read())
                        if ok:
                            st.success(f"✅ {msg}")
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")
            else:
                st.info("No server-side backups found yet.")

        with tab_list:
            st.markdown("#### Backup History")
            server_backups = list_backups()
            if server_backups:
                df_bk = pd.DataFrame([{
                    "Filename": b["name"],
                    "Timestamp": b["label"],
                    "Size (KB)": b["size_kb"],
                } for b in server_backups])
                st.dataframe(df_bk, use_container_width=True, hide_index=True)

                # Download any backup
                sel_dl = st.selectbox("Download a specific backup", [b["name"] for b in server_backups])
                sel_path = next(b["path"] for b in server_backups if b["name"] == sel_dl)
                with open(sel_path, "rb") as f:
                    bk_data = f.read()
                st.download_button(
                    "📥 Download Selected Backup",
                    data=bk_data,
                    file_name=sel_dl,
                    mime="application/zip",
                )
            else:
                st.info("No backups available yet. Create one above.")

    # ─── STUDENT LIST ────────────────────────────────────────────
    elif section == "👤 Student List":
        st.markdown('<div class="page-title">👤 Student List</div>', unsafe_allow_html=True)

        if not students:
            st.info("No students registered yet.")
            return

        df_students = pd.DataFrame(students)[["name", "index", "registered_at"]]
        df_students.columns = ["Full Name", "Index Number", "Registered At"]
        df_students.index = range(1, len(df_students) + 1)

        search = st.text_input("🔍 Search by name or index", placeholder="Type to filter…")
        if search:
            mask = (
                df_students["Full Name"].str.contains(search, case=False, na=False) |
                df_students["Index Number"].str.contains(search, case=False, na=False)
            )
            df_students = df_students[mask]

        st.markdown(f"Showing **{len(df_students)}** of **{len(students)}** students")
        st.dataframe(df_students, use_container_width=True)

        # Export student list
        c1, c2 = st.columns(2)
        with c1:
            csv = df_students.to_csv().encode()
            st.download_button(
                "📥 Download as CSV",
                data=csv,
                file_name=f"Students_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )
        with c2:
            xl = to_excel(df_students)
            st.download_button(
                "📊 Download as Excel",
                data=xl,
                file_name=f"Students_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        st.markdown("<hr class='ee-divider'>", unsafe_allow_html=True)
        st.markdown("#### 🗑️ Remove a Student")
        opts = [f"{s['index']} — {s['name']}" for s in students]
        to_del = st.selectbox("Select student to remove", opts)
        confirm_del = st.checkbox("Confirm deletion (cannot be undone)")
        if confirm_del:
            if st.button("Remove Student", type="secondary"):
                idx_del = opts.index(to_del)
                removed = students.pop(idx_del)
                _write(STUDENTS_FILE, students)
                if len(students) >= MIN_STUDENTS:
                    run_grouping()
                log_event("student_removed", {"index": removed["index"]})
                st.success(f"Removed **{removed['name']}** and re-generated groups.")
                st.rerun()

    # ─── ACTIVITY LOG ────────────────────────────────────────────
    elif section == "📋 Activity Log":
        st.markdown('<div class="page-title">📋 Activity Log</div>', unsafe_allow_html=True)
        st.markdown('<div class="page-subtitle">System event history</div>', unsafe_allow_html=True)

        if not logs:
            st.info("No activity recorded yet.")
            return

        df_log = pd.DataFrame(reversed(logs[-500:]))
        df_log["timestamp"] = pd.to_datetime(df_log["timestamp"])
        df_log["date"] = df_log["timestamp"].dt.strftime("%d %b %Y")
        df_log["time"] = df_log["timestamp"].dt.strftime("%H:%M:%S")

        # Filter
        event_types = sorted(df_log["event"].unique().tolist())
        sel_events  = st.multiselect("Filter by event type", event_types, default=event_types)
        df_log = df_log[df_log["event"].isin(sel_events)]

        st.dataframe(
            df_log[["date", "time", "event", "detail"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "date":   "Date",
                "time":   "Time",
                "event":  "Event",
                "detail": st.column_config.JsonColumn("Detail"),
            },
        )

        # Summary counts
        st.markdown("<hr class='ee-divider'>", unsafe_allow_html=True)
        st.markdown("#### Event Summary")
        summary = df_log["event"].value_counts().reset_index()
        summary.columns = ["Event", "Count"]
        st.dataframe(summary, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────
#  HELPER: DataFrame → Excel bytes
# ─────────────────────────────────────────────

def to_excel(df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=True)
        ws = writer.sheets["Sheet1"]
        for col in ws.columns:
            w = max((len(str(c.value or "")) for c in col), default=10)
            ws.column_dimensions[col[0].column_letter].width = min(w + 4, 50)
    return buf.getvalue()


# ─────────────────────────────────────────────
#  SIDEBAR SHARED UI
# ─────────────────────────────────────────────

def sidebar_ui() -> str:
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center; padding: 1rem 0 0.5rem;">
            <div style="font-size:3rem">⚡</div>
            <div style="font-family:'Space Mono',monospace; font-size:1.05rem;
                        font-weight:700; color:#f0f9ff; letter-spacing:-0.5px;">
                EE Lab Grouping
            </div>
            <div style="font-size:0.75rem; color:#7dd3fc; margin-top:2px;">
                STUBTECH Dept. of Electrical Engineering
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        page = "Student"
        if st.button("🎓 Student Portal",  use_container_width=True,
                     type="primary" if st.session_state.get("nav") == "Student" else "secondary"):
            st.session_state["nav"] = "Student"
            st.session_state["admin_auth"] = False
            st.rerun()

        if st.button("🔐 Admin Dashboard", use_container_width=True,
                     type="primary" if st.session_state.get("nav") == "Admin" else "secondary"):
            st.session_state["nav"] = "Admin"
            st.rerun()

        st.markdown("---")

        # Quick stats
        students = _read(STUDENTS_FILE) or []
        st.markdown(f"""
        <div style="font-size:0.8rem; color:#7dd3fc; padding: 0 0.25rem;">
            📌 <strong style="color:#f0f9ff">{len(students)}</strong> students registered<br>
            <span style="font-size:0.72rem; color:#4a7a9b;">
                Index format: STUBTECH + 6 digits
            </span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("""
        <div style="font-size:0.72rem; color:#4a7a9b; text-align:center; padding-bottom:0.5rem;">
            © 2024 EE Lab Grouping System<br>v1.0 — Streamlit Cloud Edition
        </div>
        """, unsafe_allow_html=True)

    return st.session_state.get("nav", "Student")


# ─────────────────────────────────────────────
#  MAIN ENTRY POINT
# ─────────────────────────────────────────────

def main():
    init_storage()

    nav = sidebar_ui()

    if nav == "Admin":
        if st.session_state.get("admin_auth", False):
            admin_page()
        else:
            admin_login_ui()
    else:
        student_page()


if __name__ == "__main__":
    main()
