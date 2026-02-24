import streamlit as st
import pandas as pd
import json
import os
import hashlib
import random
import time
from datetime import datetime
import shutil
import base64
from io import BytesIO
import plotly.express as px
import plotly.graph_objects as go
import re
from typing import Dict, List, Optional, Tuple
import zipfile

# ==================== CONFIGURATION ====================
st.set_page_config(
    page_title="Electrical Engineering Lab Grouping System",
    page_icon="🔌",
    initial_sidebar_state="expanded",
    layout="wide"
)

# ==================== CONSTANTS ====================
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = hashlib.sha256("admin123".encode()).hexdigest()

# ── Streamlit Cloud uses an ephemeral filesystem; /tmp is always writable ──
# Set DATA_DIR to a path that works both locally and on Streamlit Cloud.
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR    = os.path.join(_BASE_DIR, "data")
BACKUP_DIR  = os.path.join(_BASE_DIR, "backups")
EXPORT_DIR  = os.path.join(_BASE_DIR, "exports")

STUDENTS_FILE         = os.path.join(DATA_DIR, "students.json")
MECHTRONICS_GROUPS_FILE = os.path.join(DATA_DIR, "mechtronics_groups.json")
RENEWABLE_GROUPS_FILE = os.path.join(DATA_DIR, "renewable_groups.json")
APP_STATE_FILE        = os.path.join(DATA_DIR, "app_state.json")
LOG_FILE              = os.path.join(DATA_DIR, "system_logs.json")

# Pagination settings
PAGE_SIZE = 50

# ==================== INITIALIZATION ====================

def init_directories():
    """Create necessary directories if they don't exist."""
    for directory in [DATA_DIR, BACKUP_DIR, EXPORT_DIR]:
        os.makedirs(directory, exist_ok=True)

def init_data_files():
    """Initialize JSON data files if they don't exist."""
    files_config = {
        STUDENTS_FILE: [],
        MECHTRONICS_GROUPS_FILE: {"Group A": [], "Group B": []},
        RENEWABLE_GROUPS_FILE:   {"Group A": [], "Group B": [], "Group C": []},
        APP_STATE_FILE: {
            "last_backup": None,
            "total_students": 0,
            "last_grouping": None,
            "version": "2.0"
        },
        LOG_FILE: []
    }
    for file_path, default_data in files_config.items():
        if not os.path.exists(file_path):
            _write_json(file_path, default_data)

# ==================== DATA MANAGEMENT ====================

def _write_json(file_path: str, data) -> None:
    """Write data to a JSON file safely."""
    tmp_path = file_path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, file_path)   # atomic on POSIX
    except Exception as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise e

def load_data(file_path: str):
    """Load data from a JSON file (no caching — always fresh)."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def save_data(file_path: str, data) -> None:
    """Save data to a JSON file."""
    _write_json(file_path, data)

def log_operation(operation: str, details: Dict = None) -> None:
    """Log system operations (non-blocking; silently skips on errors)."""
    try:
        logs = load_data(LOG_FILE) or []
        logs.append({
            "operation": operation,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        })
        if len(logs) > 1000:
            logs = logs[-1000:]
        save_data(LOG_FILE, logs)
    except Exception:
        pass   # Never crash the app due to logging

def get_performance_metrics() -> Dict:
    """Get a summary of recent operations from the log."""
    logs = load_data(LOG_FILE) or []
    operations: Dict[str, Dict] = {}
    for log in logs[-100:]:
        op = log.get("operation", "unknown")
        if op not in operations:
            operations[op] = {"count": 0, "last": None}
        operations[op]["count"] += 1
        operations[op]["last"] = log.get("timestamp")
    return operations

# ==================== BACKUP ====================

def create_backup() -> Tuple[str, str]:
    """Create a timestamped backup of all data files and return (timestamp, zip_path)."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_subdir = os.path.join(BACKUP_DIR, f"backup_{timestamp}")
    os.makedirs(backup_subdir, exist_ok=True)

    backup_files = []
    for file in os.listdir(DATA_DIR):
        if file.endswith(".json"):
            src = os.path.join(DATA_DIR, file)
            dst = os.path.join(backup_subdir, file)
            shutil.copy2(src, dst)
            backup_files.append(file)

    zip_path = os.path.join(BACKUP_DIR, f"backup_{timestamp}.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file in backup_files:
            zipf.write(os.path.join(backup_subdir, file), file)

    app_state = load_data(APP_STATE_FILE) or {}
    app_state["last_backup"] = timestamp
    save_data(APP_STATE_FILE, app_state)

    log_operation("backup_created", {"timestamp": timestamp, "files": backup_files})
    return timestamp, zip_path

def restore_from_backup(backup_path: str) -> bool:
    """Restore data files from a backup directory."""
    try:
        restored = []
        for file in os.listdir(backup_path):
            if file.endswith(".json"):
                shutil.copy2(os.path.join(backup_path, file), os.path.join(DATA_DIR, file))
                restored.append(file)
        log_operation("backup_restored", {"backup": os.path.basename(backup_path), "files": restored})
        return True
    except Exception as e:
        st.error(f"Restore failed: {e}")
        return False

def list_backups() -> List[Dict]:
    """List all available backup directories, newest first."""
    if not os.path.exists(BACKUP_DIR):
        return []
    backups = []
    for item in os.listdir(BACKUP_DIR):
        item_path = os.path.join(BACKUP_DIR, item)
        if os.path.isdir(item_path) and item.startswith("backup_"):
            total_size = sum(
                os.path.getsize(os.path.join(item_path, f))
                for f in os.listdir(item_path)
            )
            backups.append({
                "name": item,
                "path": item_path,
                "timestamp": item.replace("backup_", ""),
                "size": f"{total_size / 1024:.1f} KB"
            })
    return sorted(backups, key=lambda x: x["timestamp"], reverse=True)

# ==================== VALIDATION ====================

def validate_index_number(index: str) -> bool:
    """Validate index number format: STUBTECHxxxxxx (6 digits)."""
    return bool(re.match(r"^STUBTECH\d{6}$", index.upper()))

def validate_name(name: str) -> bool:
    """Validate student name — letters, spaces, and basic punctuation."""
    stripped = name.strip()
    return len(stripped) >= 2 and all(c.isalpha() or c in " .-'\u2019" for c in stripped)

def is_duplicate_student(index: str, name: str = None) -> Tuple[bool, str]:
    """Return (is_duplicate, reason_message)."""
    students = load_data(STUDENTS_FILE) or []
    indices = {s["index"] for s in students}
    if index in indices:
        return True, "Index number already exists"
    if name:
        names = {s["name"].strip().lower() for s in students}
        if name.strip().lower() in names:
            return True, "Name already exists"
    return False, ""

# ==================== GROUPING ====================

def assign_mechtronics_groups(students: List[Dict]) -> Dict:
    """Split students randomly into two balanced Mechatronics groups."""
    if not students:
        return {"Group A": [], "Group B": []}

    shuffled = random.sample(students, len(students))
    half = len(shuffled) // 2
    remainder = len(shuffled) % 2

    def make_entry(student, letter):
        return {**student, "marks": None, "group_type": "mechatronics",
                "group_number": letter, "lab": "Mechatronics"}

    groups = {
        "Group A": [make_entry(s, "A") for s in shuffled[:half + remainder]],
        "Group B": [make_entry(s, "B") for s in shuffled[half + remainder:]]
    }
    log_operation("grouping_mechatronics", {"students": len(students),
                                            "groups": {k: len(v) for k, v in groups.items()}})
    return groups

def assign_renewable_groups(students: List[Dict]) -> Dict:
    """Split students randomly into three balanced Renewable Energy groups."""
    if not students:
        return {"Group A": [], "Group B": [], "Group C": []}

    shuffled = random.sample(students, len(students))
    total = len(shuffled)
    base_size = total // 3
    remainder = total % 3

    group_sizes = [
        base_size + (1 if remainder > 0 else 0),
        base_size + (1 if remainder > 1 else 0),
        base_size
    ]

    def make_entry(student, letter):
        return {**student, "marks": None, "group_type": "renewable",
                "group_number": letter, "lab": "Renewable Energy"}

    groups = {}
    start = 0
    for letter, size in zip(["A", "B", "C"], group_sizes):
        name = f"Group {letter}"
        groups[name] = [make_entry(s, letter) for s in shuffled[start:start + size]]
        start += size

    log_operation("grouping_renewable", {"students": total,
                                         "groups": {k: len(v) for k, v in groups.items()}})
    return groups

def reassign_groups() -> Tuple[bool, str]:
    """Regenerate both group assignments from the current student list."""
    students = load_data(STUDENTS_FILE) or []

    if len(students) < 6:
        return False, f"Need at least 6 students for grouping (currently have {len(students)})"

    save_data(MECHTRONICS_GROUPS_FILE, assign_mechtronics_groups(students))
    save_data(RENEWABLE_GROUPS_FILE,   assign_renewable_groups(students))

    app_state = load_data(APP_STATE_FILE) or {}
    app_state["last_grouping"] = datetime.now().isoformat()
    app_state["total_students"] = len(students)
    save_data(APP_STATE_FILE, app_state)

    return True, f"Groups reassigned successfully for {len(students)} students"

# ==================== UI HELPERS ====================

def paginate_dataframe(df: pd.DataFrame, key_prefix: str = "page") -> pd.DataFrame:
    """Display pagination controls and return the current page slice."""
    if len(df) <= PAGE_SIZE:
        return df

    page_key = f"{key_prefix}_number"
    if page_key not in st.session_state:
        st.session_state[page_key] = 1

    total_pages = max(1, (len(df) + PAGE_SIZE - 1) // PAGE_SIZE)
    # Clamp page in case data shrank
    st.session_state[page_key] = min(st.session_state[page_key], total_pages)

    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col1:
        if st.button("⏮ First", key=f"{key_prefix}_first"):
            st.session_state[page_key] = 1
    with col2:
        if st.button("◀ Prev", key=f"{key_prefix}_prev") and st.session_state[page_key] > 1:
            st.session_state[page_key] -= 1
    with col3:
        if st.button("Next ▶", key=f"{key_prefix}_next") and st.session_state[page_key] < total_pages:
            st.session_state[page_key] += 1
    with col4:
        if st.button("⏭ Last", key=f"{key_prefix}_last"):
            st.session_state[page_key] = total_pages

    st.caption(f"Page {st.session_state[page_key]} of {total_pages}  •  {len(df)} total records")

    start = (st.session_state[page_key] - 1) * PAGE_SIZE
    return df.iloc[start: start + PAGE_SIZE]

def show_group_statistics() -> None:
    """Display detailed statistics about group distribution."""
    students   = load_data(STUDENTS_FILE) or []
    mechtronics = load_data(MECHTRONICS_GROUPS_FILE) or {}
    renewable   = load_data(RENEWABLE_GROUPS_FILE) or {}

    if not students:
        st.info("No students registered yet")
        return

    st.header("📊 Group Distribution Statistics")

    total_mech  = sum(len(g) for g in mechtronics.values())
    total_renew = sum(len(g) for g in renewable.values())

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Students",       len(students))
    col2.metric("Mechatronics Students", total_mech)
    col3.metric("Renewable Students",   total_renew)
    balanced = "✅ Yes" if abs(total_mech - total_renew) < 3 else "⚠️ Needs review"
    col4.metric("Balanced", balanced)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🔧 Mechatronics Lab (2 Groups)")
        if mechtronics:
            data = [{"Group": g, "Students": len(m),
                     "Percentage": f"{len(m)/len(students)*100:.1f}%"}
                    for g, m in mechtronics.items()]
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
            with st.expander("View Group Samples"):
                for g, members in mechtronics.items():
                    if members:
                        st.write(f"**{g}** (first 5 of {len(members)})")
                        st.dataframe(pd.DataFrame(members[:5])[["index", "name"]],
                                     use_container_width=True, hide_index=True)

    with col2:
        st.subheader("🌱 Renewable Energy Lab (3 Groups)")
        if renewable:
            data = [{"Group": g, "Students": len(m),
                     "Percentage": f"{len(m)/len(students)*100:.1f}%"}
                    for g, m in renewable.items()]
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
            with st.expander("View Group Samples"):
                for g, members in renewable.items():
                    if members:
                        st.write(f"**{g}** (first 5 of {len(members)})")
                        st.dataframe(pd.DataFrame(members[:5])[["index", "name"]],
                                     use_container_width=True, hide_index=True)

    # Visualization
    viz_data = (
        [{"Lab": "Mechatronics", "Group": g, "Students": len(m)} for g, m in mechtronics.items()] +
        [{"Lab": "Renewable",    "Group": g, "Students": len(m)} for g, m in renewable.items()]
    )
    if viz_data:
        fig = px.bar(
            pd.DataFrame(viz_data), x="Group", y="Students", color="Lab",
            text="Students", barmode="group",
            title=f"Group Distribution for {len(students)} Students"
        )
        fig.update_traces(texttemplate="%{text}", textposition="outside")
        fig.update_layout(height=450)
        st.plotly_chart(fig, use_container_width=True)

# ==================== EXCEL EXPORT ====================

def to_excel(df: pd.DataFrame) -> bytes:
    """Convert a DataFrame to Excel bytes."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
        ws = writer.sheets["Sheet1"]
        for col in ws.columns:
            max_len = max((len(str(cell.value or "")) for cell in col), default=0)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 50)
    return output.getvalue()

def get_download_link(df: pd.DataFrame, filename: str, text: str) -> str:
    b64 = base64.b64encode(to_excel(df)).decode()
    mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return f'<a href="data:{mime};base64,{b64}" download="{filename}.xlsx">{text}</a>'

def generate_group_dataframes(groups_data: Dict, lab_type: str) -> pd.DataFrame:
    """Flatten group dicts into a single DataFrame."""
    frames = []
    for group_name, students in groups_data.items():
        if students:
            df = pd.DataFrame(students)
            df["Group"] = group_name
            df["Lab"]   = lab_type
            df["Marks"] = df.get("marks", "")
            cols = ["index", "name", "Group", "Lab", "Marks"]
            if "registration_date" in df.columns:
                cols.append("registration_date")
            frames.append(df[cols])
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def export_all_data() -> bytes:
    """Build a multi-sheet Excel export of all data."""
    students    = load_data(STUDENTS_FILE) or []
    mechtronics = load_data(MECHTRONICS_GROUPS_FILE) or {}
    renewable   = load_data(RENEWABLE_GROUPS_FILE) or {}

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        if students:
            pd.DataFrame(students).to_excel(writer, sheet_name="All Students", index=False)

        df_mech = generate_group_dataframes(mechtronics, "Mechatronics")
        if not df_mech.empty:
            df_mech.to_excel(writer, sheet_name="Mechatronics Groups", index=False)

        df_renew = generate_group_dataframes(renewable, "Renewable Energy")
        if not df_renew.empty:
            df_renew.to_excel(writer, sheet_name="Renewable Groups", index=False)

        stats = [
            ["Total Students",       len(students)],
            ["Mechatronics Groups",  sum(len(g) for g in mechtronics.values())],
            ["Renewable Groups",     sum(len(g) for g in renewable.values())],
            ["Generated",            datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
        ]
        pd.DataFrame(stats, columns=["Metric", "Value"]).to_excel(
            writer, sheet_name="Statistics", index=False)

    return output.getvalue()

# ==================== AUTHENTICATION ====================

def check_password() -> bool:
    """Return True if the admin is authenticated."""
    if st.session_state.get("password_correct", False):
        return True

    with st.form("Credentials"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if submitted:
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        if username == ADMIN_USERNAME and pw_hash == ADMIN_PASSWORD_HASH:
            st.session_state["password_correct"] = True
            log_operation("admin_login", {"username": ADMIN_USERNAME})
            st.rerun()
        else:
            st.error("❌ Invalid username or password")
            log_operation("failed_login", {"username": username})

    return False

# ==================== STUDENT INTERFACE ====================

def student_interface() -> None:
    st.title("📝 Student Registration")
    st.markdown("Please fill in your details to register for Electrical Engineering Labs")

    col1, col2 = st.columns([2, 1])

    with col1:
        with st.form("student_registration", clear_on_submit=True):
            st.subheader("Registration Form")
            name  = st.text_input("Full Name",     placeholder="Enter your full name",
                                  help="Use your official name as registered")
            index = st.text_input("Index Number", placeholder="STUBTECH220457",
                                  help="Format: STUBTECH followed by 6 digits")
            submitted = st.form_submit_button("📝 Register", use_container_width=True, type="primary")

        # Handle form submission OUTSIDE the form to avoid nested-button issues
        if submitted:
            error_msg = None
            if not name or not index:
                error_msg = "Please fill in all fields"
            elif not validate_name(name):
                error_msg = "Please enter a valid name (letters, spaces, and basic punctuation only)"
            elif not validate_index_number(index):
                error_msg = "Invalid index number format. Use STUBTECH followed by 6 digits (e.g., STUBTECH220457)"
            else:
                is_dup, dup_msg = is_duplicate_student(index.upper(), name)
                if is_dup:
                    error_msg = dup_msg

            if error_msg:
                st.error(f"❌ {error_msg}")
            else:
                students = load_data(STUDENTS_FILE) or []
                students.append({
                    "name": name.strip(),
                    "index": index.upper(),
                    "registration_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                save_data(STUDENTS_FILE, students)

                if len(students) >= 6:
                    reassign_groups()

                log_operation("student_registered", {
                    "index": index.upper(), "total_students": len(students)
                })
                st.success("✅ Registration successful!")
                st.balloons()
                st.rerun()

    with col2:
        students = load_data(STUDENTS_FILE) or []
        st.subheader("📊 Current Statistics")
        if students:
            st.metric("Total Registered", len(students))
            st.metric("Date", datetime.now().strftime("%d %b %Y"))
            with st.expander("Recent Registrations"):
                for s in reversed(students[-5:]):
                    st.caption(f"• {s['name']} ({s['index']})")
        else:
            st.info("No students registered yet")
            st.caption("Be the first to register!")

# ==================== ADMIN INTERFACE ====================

def admin_interface() -> None:
    st.title("👨‍🏫 Admin Dashboard")

    admin_action = st.sidebar.selectbox(
        "📋 Admin Actions",
        ["Dashboard", "View Students", "Manage Groups",
         "Backup & Restore", "Generate Reports", "System Logs"]
    )

    with st.sidebar.expander("📊 System Status", expanded=False):
        students = load_data(STUDENTS_FILE) or []
        st.metric("Total Students", len(students))
        metrics = get_performance_metrics()
        if metrics:
            st.write("**Recent Operations:**")
            for op, data in list(metrics.items())[:3]:
                st.caption(f"• {op}: {data['count']}×")

    if admin_action == "Dashboard":
        show_admin_dashboard()
    elif admin_action == "View Students":
        manage_students()
    elif admin_action == "Manage Groups":
        manage_groups()
    elif admin_action == "Backup & Restore":
        backup_interface()
    elif admin_action == "Generate Reports":
        generate_reports()
    elif admin_action == "System Logs":
        show_system_logs()

def show_admin_dashboard() -> None:
    st.header("📊 Dashboard")

    students    = load_data(STUDENTS_FILE) or []
    mechtronics = load_data(MECHTRONICS_GROUPS_FILE) or {}
    renewable   = load_data(RENEWABLE_GROUPS_FILE) or {}
    app_state   = load_data(APP_STATE_FILE) or {}

    total_mech  = sum(len(g) for g in mechtronics.values())
    total_renew = sum(len(g) for g in renewable.values())

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Students",  len(students))
    col2.metric("Mechatronics",    total_mech,
                delta=f"{total_mech/len(students)*100:.0f}%" if students else "0%")
    col3.metric("Renewable",       total_renew,
                delta=f"{total_renew/len(students)*100:.0f}%" if students else "0%")

    last_backup = app_state.get("last_backup") or "Never"
    if last_backup != "Never":
        last_backup = last_backup.replace("_", " at ")
    col4.metric("Last Backup", last_backup)

    last_grouping = app_state.get("last_grouping") or "Never"
    if last_grouping != "Never":
        last_grouping = last_grouping[:10]
    col5.metric("Last Grouping", last_grouping)

    if students:
        show_group_statistics()
    else:
        st.info("No students registered yet. Groups will be created once students register.")

    st.markdown("---")
    st.subheader("⚡ Quick Actions")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("🔄 Reassign Groups", use_container_width=True, type="primary"):
            with st.spinner("Reassigning groups…"):
                success, message = reassign_groups()
            if success:
                st.success(message)
                time.sleep(0.5)
                st.rerun()
            else:
                st.warning(message)

    with col2:
        if st.button("💾 Create Backup", use_container_width=True):
            timestamp, zip_path = create_backup()
            st.success(f"Backup created: {timestamp}")
            with open(zip_path, "rb") as f:
                st.download_button(
                    "📥 Download Backup",
                    data=f.read(),
                    file_name=f"backup_{timestamp}.zip",
                    mime="application/zip",
                    key=f"dl_backup_{timestamp}"
                )

    with col3:
        if st.button("📥 Export All Data", use_container_width=True):
            excel_data = export_all_data()
            st.download_button(
                "📥 Download Export",
                data=excel_data,
                file_name="lab_grouping_export.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_export_all"
            )

    with col4:
        if st.button("🧹 Clear Cache", use_container_width=True):
            # Streamlit's built-in cache clear (safe to call)
            st.cache_data.clear()
            st.success("Cache cleared!")

def manage_students() -> None:
    st.header("📋 Student Management")

    students = load_data(STUDENTS_FILE) or []
    if not students:
        st.info("No students registered yet")
        return

    col1, col2 = st.columns([3, 1])
    with col1:
        search  = st.text_input("🔍 Search by name or index", placeholder="Type to search…")
    with col2:
        sort_by = st.selectbox("Sort by", ["Name", "Index", "Date"])

    df = pd.DataFrame(students)

    if search:
        mask = (
            df["name"].str.contains(search, case=False, na=False) |
            df["index"].str.contains(search, case=False, na=False)
        )
        df = df[mask]

    if sort_by == "Name":
        df = df.sort_values("name")
    elif sort_by == "Index":
        df = df.sort_values("index")
    elif sort_by == "Date" and "registration_date" in df.columns:
        df = df.sort_values("registration_date", ascending=False)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Students", len(students))
    col2.metric("Showing",        len(df))
    col3.metric("Pages",          max(1, (len(df) + PAGE_SIZE - 1) // PAGE_SIZE))

    df_paginated = paginate_dataframe(df, key_prefix="students")

    st.dataframe(
        df_paginated,
        use_container_width=True,
        column_config={
            "name":              "Student Name",
            "index":             "Index Number",
            "registration_date": "Registration Date"
        },
        hide_index=True
    )

    # ── CSV export ──
    with st.expander("📤 Export Students"):
        csv = df.to_csv(index=False).encode()
        st.download_button(
            "Download as CSV",
            data=csv,
            file_name="students_export.csv",
            mime="text/csv"
        )

    # ── Delete individual student ──
    with st.expander("🗑️ Delete Individual Student"):
        options = [f"{s['index']} – {s['name']}" for s in students]
        student_to_delete = st.selectbox("Select student to delete", options)

        # Use a confirmation checkbox before showing the delete button
        confirm = st.checkbox("I understand this action cannot be undone", key="confirm_del_single")
        if confirm:
            if st.button("🗑️ Delete Selected Student", type="secondary"):
                idx = options.index(student_to_delete)
                deleted = students.pop(idx)
                save_data(STUDENTS_FILE, students)
                reassign_groups()
                log_operation("student_deleted", {"index": deleted["index"]})
                st.success(f"Deleted {deleted['name']}")
                st.rerun()

    # ── Delete ALL students ──
    with st.expander("⚠️ Delete ALL Students"):
        confirm_all = st.checkbox("I understand ALL students will be removed", key="confirm_del_all")
        if confirm_all:
            if st.button("🗑️ Delete ALL Students", type="secondary", key="del_all_btn"):
                save_data(STUDENTS_FILE, [])
                save_data(MECHTRONICS_GROUPS_FILE, {"Group A": [], "Group B": []})
                save_data(RENEWABLE_GROUPS_FILE,   {"Group A": [], "Group B": [], "Group C": []})
                log_operation("all_students_deleted", {})
                st.success("All students deleted!")
                st.rerun()

def manage_groups() -> None:
    st.header("👥 Group Management")

    students    = load_data(STUDENTS_FILE) or []
    mechtronics = load_data(MECHTRONICS_GROUPS_FILE) or {}
    renewable   = load_data(RENEWABLE_GROUPS_FILE) or {}

    if not students:
        st.info("No students registered yet")
        return

    tab1, tab2, tab3 = st.tabs(["Mechatronics Lab", "Renewable Energy Lab", "Comparison"])

    with tab1:
        st.markdown("### 🔧 Mechatronics Lab Groups")
        cols = st.columns(2)
        for idx, (group_name, members) in enumerate(mechtronics.items()):
            with cols[idx % 2]:
                with st.expander(f"{group_name} ({len(members)} students)", expanded=True):
                    if members:
                        df = pd.DataFrame(members)[["index", "name"]]
                        st.dataframe(df.head(20), use_container_width=True, hide_index=True)
                        if len(members) > 20:
                            st.caption(f"Showing first 20 of {len(members)}")
                        csv = df.to_csv(index=False).encode()
                        st.download_button(
                            f"📥 Export {group_name}",
                            data=csv,
                            file_name=f"{group_name}_mechatronics.csv",
                            mime="text/csv",
                            key=f"dl_mech_{group_name}"
                        )
                    else:
                        st.write("No students in this group")

    with tab2:
        st.markdown("### 🌱 Renewable Energy Lab Groups")
        cols = st.columns(3)
        for idx, (group_name, members) in enumerate(renewable.items()):
            with cols[idx % 3]:
                with st.expander(f"{group_name} ({len(members)} students)", expanded=True):
                    if members:
                        df = pd.DataFrame(members)[["index", "name"]]
                        st.dataframe(df.head(15), use_container_width=True, hide_index=True)
                        if len(members) > 15:
                            st.caption(f"Showing first 15 of {len(members)}")
                        csv = df.to_csv(index=False).encode()
                        st.download_button(
                            f"📥 Export {group_name}",
                            data=csv,
                            file_name=f"{group_name}_renewable.csv",
                            mime="text/csv",
                            key=f"dl_renew_{group_name}"
                        )
                    else:
                        st.write("No students in this group")

    with tab3:
        st.markdown("### 📈 Group Comparison")
        comp = (
            [{"Lab": "Mechatronics", "Group": g, "Students": len(m),
              "Percentage": f"{len(m)/len(students)*100:.1f}%"} for g, m in mechtronics.items()] +
            [{"Lab": "Renewable",    "Group": g, "Students": len(m),
              "Percentage": f"{len(m)/len(students)*100:.1f}%"} for g, m in renewable.items()]
        )
        if comp:
            df_comp = pd.DataFrame(comp)
            fig = px.bar(df_comp, x="Group", y="Students", color="Lab",
                         text="Students", barmode="group", title="Group Size Comparison")
            fig.update_traces(texttemplate="%{text}", textposition="outside")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df_comp, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("🔄 Group Controls")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🔄 Reassign All Groups", use_container_width=True, type="primary"):
            with st.spinner("Reassigning groups…"):
                success, message = reassign_groups()
            if success:
                st.success(message)
                time.sleep(0.5)
                st.rerun()
            else:
                st.warning(message)

    with col2:
        if st.button("📊 View Distribution", use_container_width=True):
            show_group_statistics()

    with col3:
        mech_df  = generate_group_dataframes(mechtronics, "Mechatronics")
        renew_df = generate_group_dataframes(renewable,   "Renewable Energy")
        if not mech_df.empty and not renew_df.empty:
            combined = pd.concat([mech_df, renew_df], ignore_index=True)
            st.download_button(
                "📥 Export All Groups",
                data=to_excel(combined),
                file_name="all_groups.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

def backup_interface() -> None:
    st.header("💾 Backup & Restore")

    tab1, tab2 = st.tabs(["Create Backup", "Restore Backup"])

    with tab1:
        st.subheader("Create New Backup")
        if st.button("📀 Create Backup Now", type="primary"):
            with st.spinner("Creating backup…"):
                timestamp, zip_path = create_backup()
            st.success(f"✅ Backup created: {timestamp}")
            with open(zip_path, "rb") as f:
                st.download_button(
                    "📥 Download Backup ZIP",
                    data=f.read(),
                    file_name=f"backup_{timestamp}.zip",
                    mime="application/zip",
                    key=f"dl_bk_{timestamp}"
                )

        st.subheader("Recent Backups")
        backups = list_backups()[:5]
        if backups:
            for backup in backups:
                with st.expander(f"📁 {backup['name']}"):
                    st.write(f"**Timestamp:** {backup['timestamp']}")
                    st.write(f"**Size:** {backup['size']}")
                    for file in os.listdir(backup["path"]):
                        st.caption(f"  • {file}")
        else:
            st.info("No backups available yet")

    with tab2:
        st.subheader("Restore from Backup")
        backups = list_backups()
        if not backups:
            st.info("No backups available to restore")
            return

        options  = [f"{b['name']} ({b['timestamp']})" for b in backups]
        selected = st.selectbox("Select backup to restore", options)
        idx      = options.index(selected)
        backup   = backups[idx]

        with st.expander("Preview Backup"):
            st.write(f"**Created:** {backup['timestamp']}  •  **Size:** {backup['size']}")
            for file in os.listdir(backup["path"]):
                st.caption(f"  • {file}")

        confirm = st.checkbox("I understand this will overwrite current data")
        if confirm:
            if st.button("⚠️ Restore Backup", type="secondary"):
                with st.spinner("Restoring…"):
                    ok = restore_from_backup(backup["path"])
                if ok:
                    st.success("✅ Backup restored successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to restore backup")

def generate_reports() -> None:
    st.header("📑 Generate Reports")

    students    = load_data(STUDENTS_FILE) or []
    mechtronics = load_data(MECHTRONICS_GROUPS_FILE) or {}
    renewable   = load_data(RENEWABLE_GROUPS_FILE) or {}

    if not students:
        st.info("No students registered yet")
        return

    report_type = st.radio(
        "Select Report Type",
        ["Mechatronics Lab", "Renewable Energy Lab", "Combined Report", "Complete Export"],
        horizontal=True
    )

    def _marks_editor(df: pd.DataFrame, groups_dict: Dict, file_path: str, lab_key: str):
        """Render an editable marks table and save button."""
        df = df.copy()
        df["Marks"] = pd.to_numeric(df.get("Marks", ""), errors="coerce")

        edited = st.data_editor(
            df,
            use_container_width=True,
            column_config={
                "index": "Index Number",
                "name":  "Student Name",
                "Group": "Group",
                "Lab":   "Lab",
                "Marks": st.column_config.NumberColumn("Marks", min_value=0, max_value=100)
            },
            disabled=["index", "name", "Group", "Lab"],
            hide_index=True,
            key=f"editor_{lab_key}"
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            st.download_button(
                "📥 Excel",
                data=to_excel(df),
                file_name=f"{lab_key}_groups.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"dl_xl_{lab_key}"
            )
        with col2:
            st.download_button(
                "📥 CSV",
                data=df.to_csv(index=False).encode(),
                file_name=f"{lab_key}_groups.csv",
                mime="text/csv",
                key=f"dl_csv_{lab_key}"
            )
        with col3:
            if st.button("💾 Save Marks", type="primary", key=f"save_{lab_key}"):
                for _, row in edited.iterrows():
                    for group in groups_dict.values():
                        for student in group:
                            if student["index"] == row["index"]:
                                student["marks"] = row.get("Marks")
                save_data(file_path, groups_dict)
                st.success("Marks saved!")

    if report_type == "Mechatronics Lab":
        df = generate_group_dataframes(mechtronics, "Mechatronics")
        if not df.empty:
            st.subheader(f"Mechatronics Lab Groups ({len(df)} students)")
            _marks_editor(df, mechtronics, MECHTRONICS_GROUPS_FILE, "mechatronics")
        else:
            st.info("No Mechatronics group data available")

    elif report_type == "Renewable Energy Lab":
        df = generate_group_dataframes(renewable, "Renewable Energy")
        if not df.empty:
            st.subheader(f"Renewable Energy Lab Groups ({len(df)} students)")
            _marks_editor(df, renewable, RENEWABLE_GROUPS_FILE, "renewable")
        else:
            st.info("No Renewable Energy group data available")

    elif report_type == "Combined Report":
        df1 = generate_group_dataframes(mechtronics, "Mechatronics")
        df2 = generate_group_dataframes(renewable,   "Renewable Energy")
        if not df1.empty and not df2.empty:
            combined = pd.concat([df1, df2], ignore_index=True)
            st.subheader(f"Combined Report ({len(combined)} students)")
            st.dataframe(combined, use_container_width=True, hide_index=True)
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "📥 Excel", data=to_excel(combined),
                    file_name="combined_groups.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            with col2:
                st.download_button(
                    "📥 CSV", data=combined.to_csv(index=False).encode(),
                    file_name="combined_groups.csv", mime="text/csv"
                )
        else:
            st.info("No group data available yet")

    else:  # Complete Export
        st.subheader("Complete Data Export")
        if st.button("📦 Generate Complete Export", type="primary"):
            st.download_button(
                "📥 Download (Multi-sheet Excel)",
                data=export_all_data(),
                file_name="complete_lab_export.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_complete"
            )

def show_system_logs() -> None:
    st.header("📋 System Logs")
    logs = load_data(LOG_FILE) or []

    if not logs:
        st.info("No logs available")
        return

    recent_logs = logs[-500:]
    operations  = sorted({log.get("operation", "") for log in recent_logs})

    col1, col2 = st.columns(2)
    with col1:
        op_filter = st.multiselect("Filter by Operation", options=operations)
    with col2:
        # date_input returns a single date or a tuple; handle both
        date_val = st.date_input("Start Date (filter from)", value=datetime.now().date())
        if isinstance(date_val, (list, tuple)):
            start_date = date_val[0] if date_val else None
        else:
            start_date = date_val

    filtered = recent_logs
    if op_filter:
        filtered = [l for l in filtered if l.get("operation") in op_filter]

    df_logs = pd.DataFrame(filtered)
    if df_logs.empty:
        st.info("No logs match the filters")
        return

    df_logs["timestamp"] = pd.to_datetime(df_logs["timestamp"])
    if start_date:
        df_logs = df_logs[df_logs["timestamp"].dt.date >= start_date]

    df_logs["date"] = df_logs["timestamp"].dt.date
    df_logs["time"] = df_logs["timestamp"].dt.time

    st.dataframe(
        df_logs[["date", "time", "operation", "details"]],
        use_container_width=True,
        column_config={"details": st.column_config.JsonColumn("Details")},
        hide_index=True
    )

    st.subheader("📊 Operation Statistics")
    stats = df_logs["operation"].value_counts().reset_index()
    stats.columns = ["Operation", "Count"]

    col1, col2 = st.columns(2)
    with col1:
        st.dataframe(stats, use_container_width=True, hide_index=True)
    with col2:
        fig = px.pie(stats, values="Count", names="Operation", title="Operation Distribution")
        st.plotly_chart(fig, use_container_width=True)

# ==================== MAIN ====================

def main() -> None:
    init_directories()
    init_data_files()

    with st.sidebar:
        # Use text/emoji instead of an external image URL — avoids network errors on Cloud
        st.markdown("## 🔌 EE Lab Grouping")
        st.markdown("---")

        if st.button("🎓 Student Portal", use_container_width=True):
            st.session_state.page = "Student"
            # Reset admin auth so someone can switch without confusion
            st.session_state.pop("password_correct", None)

        if st.button("👨‍🏫 Admin Portal", use_container_width=True):
            st.session_state.page = "Admin"

        st.markdown("---")
        students = load_data(STUDENTS_FILE) or []
        st.metric("Total Students", len(students))
        if students:
            st.caption(f"Last: {students[-1].get('registration_date', 'N/A')[:10]}")

        st.markdown("---")
        st.caption("© 2024 Electrical Engineering")
        st.caption("v2.1 – Cloud Ready")

    page = st.session_state.get("page", "Student")

    if page == "Admin":
        if check_password():
            admin_interface()
    else:
        st.session_state.page = "Student"
        student_interface()

if __name__ == "__main__":
    main()
