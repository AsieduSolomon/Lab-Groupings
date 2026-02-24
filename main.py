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
DATA_DIR = "data"
BACKUP_DIR = "backups"
EXPORT_DIR = "exports"
STUDENTS_FILE = os.path.join(DATA_DIR, "students.json")
MECHTRONICS_GROUPS_FILE = os.path.join(DATA_DIR, "mechtronics_groups.json")
RENEWABLE_GROUPS_FILE = os.path.join(DATA_DIR, "renewable_groups.json")
APP_STATE_FILE = os.path.join(DATA_DIR, "app_state.json")
LOG_FILE = os.path.join(DATA_DIR, "system_logs.json")

# Pagination settings
PAGE_SIZE = 50
MAX_DISPLAY_ROWS = 100

# ==================== INITIALIZATION FUNCTIONS ====================

def init_directories():
    """Create necessary directories if they don't exist"""
    for directory in [DATA_DIR, BACKUP_DIR, EXPORT_DIR]:
        if not os.path.exists(directory):
            os.makedirs(directory)

def init_data_files():
    """Initialize JSON data files if they don't exist"""
    files_config = {
        STUDENTS_FILE: [],
        MECHTRONICS_GROUPS_FILE: {"Group A": [], "Group B": []},
        RENEWABLE_GROUPS_FILE: {"Group A": [], "Group B": [], "Group C": []},
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
            with open(file_path, 'w') as f:
                json.dump(default_data, f, indent=2)

# ==================== DATA MANAGEMENT FUNCTIONS ====================

@st.cache_data(ttl=60)  # Cache for 60 seconds
def load_data_cached(file_path):
    """Load data from JSON file with caching"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def load_data(file_path):
    """Load data from JSON file without caching"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def save_data(file_path, data):
    """Save data to JSON file and clear cache"""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
    # Clear cache for this file
    st.cache_data.clear()

def log_operation(operation: str, details: Dict = None):
    """Log system operations for monitoring"""
    logs = load_data(LOG_FILE) or []
    logs.append({
        'operation': operation,
        'details': details or {},
        'timestamp': datetime.now().isoformat()
    })
    # Keep only last 1000 logs
    if len(logs) > 1000:
        logs = logs[-1000:]
    save_data(LOG_FILE, logs)

def get_performance_metrics():
    """Get system performance metrics"""
    logs = load_data(LOG_FILE) or []
    if not logs:
        return {}
    
    operations = {}
    for log in logs[-100:]:  # Last 100 operations
        op = log['operation']
        if op not in operations:
            operations[op] = {'count': 0, 'last': None}
        operations[op]['count'] += 1
        operations[op]['last'] = log['timestamp']
    
    return operations

# ==================== BACKUP FUNCTIONS ====================

def create_backup():
    """Create a backup of all data files with compression"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_subdir = os.path.join(BACKUP_DIR, f"backup_{timestamp}")
    os.makedirs(backup_subdir, exist_ok=True)
    
    # Copy all JSON files from data directory
    backup_files = []
    for file in os.listdir(DATA_DIR):
        if file.endswith('.json'):
            src = os.path.join(DATA_DIR, file)
            dst = os.path.join(backup_subdir, file)
            shutil.copy2(src, dst)
            backup_files.append(file)
    
    # Create a zip archive for easy download
    zip_path = os.path.join(BACKUP_DIR, f"backup_{timestamp}.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in backup_files:
            zipf.write(os.path.join(backup_subdir, file), file)
    
    # Update last backup time
    app_state = load_data(APP_STATE_FILE) or {}
    app_state['last_backup'] = timestamp
    save_data(APP_STATE_FILE, app_state)
    
    log_operation("backup_created", {"timestamp": timestamp, "files": backup_files})
    
    return timestamp, zip_path

def restore_from_backup(backup_path):
    """Restore data from a backup"""
    restored_files = []
    for file in os.listdir(backup_path):
        if file.endswith('.json'):
            src = os.path.join(backup_path, file)
            dst = os.path.join(DATA_DIR, file)
            shutil.copy2(src, dst)
            restored_files.append(file)
    
    log_operation("backup_restored", {"backup": os.path.basename(backup_path), "files": restored_files})
    st.cache_data.clear()
    return True

def list_backups():
    """List all available backups"""
    if not os.path.exists(BACKUP_DIR):
        return []
    
    backups = []
    for item in os.listdir(BACKUP_DIR):
        item_path = os.path.join(BACKUP_DIR, item)
        if os.path.isdir(item_path) and item.startswith('backup_'):
            # Get backup size
            total_size = 0
            for file in os.listdir(item_path):
                file_path = os.path.join(item_path, file)
                total_size += os.path.getsize(file_path)
            
            backups.append({
                'name': item,
                'path': item_path,
                'timestamp': item.replace('backup_', ''),
                'size': f"{total_size / 1024:.1f} KB"
            })
    return sorted(backups, key=lambda x: x['timestamp'], reverse=True)

# ==================== VALIDATION FUNCTIONS ====================

def validate_index_number(index):
    """Validate index number format (STUBTECHxxxxxx)"""
    pattern = r'^STUBTECH\d{6}$'
    return re.match(pattern, index.upper()) is not None

def validate_name(name):
    """Validate student name"""
    return len(name.strip()) >= 2 and all(c.isalpha() or c.isspace() or c in ".-'’" for c in name)

def is_duplicate_student(index, name=None):
    """Check if student already exists - optimized for large datasets"""
    students = load_data(STUDENTS_FILE) or []
    
    # Use set for faster lookup if dataset is large
    if len(students) > 100:
        indices = {s['index'] for s in students}
        if index in indices:
            return True, "Index number already exists"
        
        if name:
            names = {s['name'].lower() for s in students}
            if name.lower() in names:
                return True, "Name already exists"
    else:
        # Linear search for smaller datasets
        for student in students:
            if student['index'] == index:
                return True, "Index number already exists"
            if name and student['name'].lower() == name.lower():
                return True, "Name already exists"
    
    return False, ""

# ==================== ENHANCED GROUPING FUNCTIONS ====================

def assign_mechtronics_groups_scalable(students: List[Dict]) -> Dict:
    """
    Enhanced grouping function optimized for large numbers of students
    Ensures perfectly balanced groups with O(n) complexity
    """
    if not students:
        return {"Group A": [], "Group B": []}
    
    start_time = time.time()
    
    # Use random.sample for more efficient shuffling
    shuffled = random.sample(students, len(students))
    total = len(shuffled)
    
    # Calculate perfect split
    half = total // 2
    remainder = total % 2
    
    # Bulk create group entries (much faster than appending one by one)
    groups = {
        "Group A": [
            {
                **student,
                'marks': None,
                'group_type': 'mechatronics',
                'group_number': 'A',
                'lab': 'Mechatronics'
            }
            for student in shuffled[:half + remainder]
        ],
        
        "Group B": [
            {
                **student,
                'marks': None,
                'group_type': 'mechatronics',
                'group_number': 'B',
                'lab': 'Mechatronics'
            }
            for student in shuffled[half + remainder:]
        ]
    }
    
    duration = time.time() - start_time
    log_operation("grouping_mechatronics", {
        "students": total,
        "duration": duration,
        "groups": {k: len(v) for k, v in groups.items()}
    })
    
    return groups

def assign_renewable_groups_scalable(students: List[Dict]) -> Dict:
    """
    Enhanced 3-group assignment optimized for large numbers
    Ensures perfectly balanced groups with O(n) complexity
    """
    if not students:
        return {"Group A": [], "Group B": [], "Group C": []}
    
    start_time = time.time()
    
    shuffled = random.sample(students, len(students))
    total = len(shuffled)
    
    # Calculate optimal group sizes
    base_size = total // 3
    remainder = total % 3
    
    groups = {
        "Group A": [],
        "Group B": [],
        "Group C": []
    }
    
    # Bulk assignment by slices (more efficient)
    start_idx = 0
    group_sizes = [
        base_size + (1 if remainder > 0 else 0),
        base_size + (1 if remainder > 1 else 0),
        base_size
    ]
    
    for i, (group_name, size) in enumerate(zip(["Group A", "Group B", "Group C"], group_sizes)):
        end_idx = start_idx + size
        groups[group_name] = [
            {
                **student,
                'marks': None,
                'group_type': 'renewable',
                'group_number': group_name[-1],
                'lab': 'Renewable Energy'
            }
            for student in shuffled[start_idx:end_idx]
        ]
        start_idx = end_idx
    
    duration = time.time() - start_time
    log_operation("grouping_renewable", {
        "students": total,
        "duration": duration,
        "groups": {k: len(v) for k, v in groups.items()}
    })
    
    return groups

def reassign_groups_scalable():
    """Regenerate both group assignments with performance optimization"""
    students = load_data(STUDENTS_FILE) or []
    
    if len(students) < 6:
        return False, f"Need at least 6 students for proper grouping (currently have {len(students)})"
    
    # Create groups
    mechtronics_groups = assign_mechtronics_groups_scalable(students)
    renewable_groups = assign_renewable_groups_scalable(students)
    
    # Save data
    save_data(MECHTRONICS_GROUPS_FILE, mechtronics_groups)
    save_data(RENEWABLE_GROUPS_FILE, renewable_groups)
    
    # Update app state
    app_state = load_data(APP_STATE_FILE) or {}
    app_state['last_grouping'] = datetime.now().isoformat()
    app_state['total_students'] = len(students)
    save_data(APP_STATE_FILE, app_state)
    
    # Auto backup if significant change
    if len(students) % 50 == 0:  # Backup every 50 new students
        create_backup()
    
    return True, f"Groups reassigned successfully for {len(students)} students"

# ==================== UI HELPER FUNCTIONS ====================

def paginate_dataframe(df: pd.DataFrame, page_size: int = PAGE_SIZE) -> pd.DataFrame:
    """Add pagination for large dataframes"""
    if len(df) <= page_size:
        return df
    
    # Initialize page number in session state
    if 'page_number' not in st.session_state:
        st.session_state.page_number = 1
    
    total_pages = (len(df) + page_size - 1) // page_size
    
    # Navigation
    col1, col2, col3, col4 = st.columns([1, 2, 2, 1])
    
    with col1:
        if st.button("⏮ First"):
            st.session_state.page_number = 1
    
    with col2:
        if st.button("◀ Previous") and st.session_state.page_number > 1:
            st.session_state.page_number -= 1
    
    with col3:
        if st.button("Next ▶") and st.session_state.page_number < total_pages:
            st.session_state.page_number += 1
    
    with col4:
        if st.button("⏭ Last"):
            st.session_state.page_number = total_pages
    
    st.caption(f"Page {st.session_state.page_number} of {total_pages} (Total: {len(df)} records)")
    
    # Get current page data
    start_idx = (st.session_state.page_number - 1) * page_size
    end_idx = min(start_idx + page_size, len(df))
    
    return df.iloc[start_idx:end_idx]

def show_group_statistics():
    """Display detailed statistics about group distribution"""
    students = load_data(STUDENTS_FILE) or []
    mechtronics = load_data(MECHTRONICS_GROUPS_FILE) or {}
    renewable = load_data(RENEWABLE_GROUPS_FILE) or {}
    
    if not students:
        st.info("No students registered yet")
        return
    
    st.header("📊 Group Distribution Statistics")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Students", len(students))
    with col2:
        total_mech = sum(len(g) for g in mechtronics.values())
        st.metric("Mechatronics Students", total_mech)
    with col3:
        total_renew = sum(len(g) for g in renewable.values())
        st.metric("Renewable Students", total_renew)
    with col4:
        balanced = "✅ Yes" if abs(total_mech - total_renew) < 3 else "⚠️ Needs review"
        st.metric("Balanced", balanced)
    
    # Detailed group breakdown
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔧 Mechatronics Lab (2 Groups)")
        if mechtronics:
            data = []
            for group_name, members in mechtronics.items():
                data.append({
                    'Group': group_name,
                    'Students': len(members),
                    'Percentage': f"{len(members)/len(students)*100:.1f}%"
                })
            df_mech = pd.DataFrame(data)
            st.dataframe(df_mech, use_container_width=True, hide_index=True)
            
            # Show sample
            with st.expander("View Group Samples"):
                for group_name, members in mechtronics.items():
                    if members:
                        st.write(f"**{group_name}** (showing first 5 of {len(members)})")
                        sample_df = pd.DataFrame(members[:5])[['index', 'name']]
                        st.dataframe(sample_df, use_container_width=True, hide_index=True)
    
    with col2:
        st.subheader("🌱 Renewable Energy Lab (3 Groups)")
        if renewable:
            data = []
            for group_name, members in renewable.items():
                data.append({
                    'Group': group_name,
                    'Students': len(members),
                    'Percentage': f"{len(members)/len(students)*100:.1f}%"
                })
            df_renew = pd.DataFrame(data)
            st.dataframe(df_renew, use_container_width=True, hide_index=True)
            
            # Show sample
            with st.expander("View Group Samples"):
                for group_name, members in renewable.items():
                    if members:
                        st.write(f"**{group_name}** (showing first 5 of {len(members)})")
                        sample_df = pd.DataFrame(members[:5])[['index', 'name']]
                        st.dataframe(sample_df, use_container_width=True, hide_index=True)
    
    # Visualization
    st.subheader("Group Size Comparison")
    
    # Prepare data for visualization
    viz_data = []
    for group_name, members in mechtronics.items():
        viz_data.append({
            'Lab': 'Mechatronics',
            'Group': group_name,
            'Students': len(members)
        })
    
    for group_name, members in renewable.items():
        viz_data.append({
            'Lab': 'Renewable',
            'Group': group_name,
            'Students': len(members)
        })
    
    if viz_data:
        df_viz = pd.DataFrame(viz_data)
        
        # Create bar chart
        fig = px.bar(
            df_viz,
            x='Group',
            y='Students',
            color='Lab',
            title=f'Group Distribution for {len(students)} Students',
            text='Students',
            barmode='group'
        )
        fig.update_traces(texttemplate='%{text}', textposition='outside')
        fig.update_layout(
            uniformtext_minsize=8,
            uniformtext_mode='hide',
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)

# ==================== EXCEL/PDF GENERATION ====================

def to_excel(df: pd.DataFrame) -> bytes:
    """Convert DataFrame to Excel download"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
        
        # Auto-adjust column widths
        for sheet in writer.sheets.values():
            for column in sheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                sheet.column_dimensions[column_letter].width = adjusted_width
    
    return output.getvalue()

def get_download_link(df: pd.DataFrame, filename: str, text: str) -> str:
    """Generate download link for Excel file"""
    excel_data = to_excel(df)
    b64 = base64.b64encode(excel_data).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}.xlsx" style="text-decoration: none;">{text}</a>'
    return href

def generate_group_dataframes(groups_data: Dict, lab_type: str) -> pd.DataFrame:
    """Generate DataFrames for groups with marks column"""
    all_dfs = []
    
    for group_name, students in groups_data.items():
        if students:
            df = pd.DataFrame(students)
            if not df.empty:
                df['Group'] = group_name
                df['Lab'] = lab_type
                df['Marks'] = df.get('marks', '')
                
                # Ensure columns exist
                columns = ['index', 'name', 'Group', 'Lab', 'Marks']
                if 'registration_date' in df.columns:
                    columns.append('registration_date')
                
                df = df[columns]
                all_dfs.append(df)
    
    if all_dfs:
        return pd.concat(all_dfs, ignore_index=True)
    return pd.DataFrame()

def export_all_data():
    """Export all data as a single Excel file with multiple sheets"""
    students = load_data(STUDENTS_FILE) or []
    mechtronics = load_data(MECHTRONICS_GROUPS_FILE) or {}
    renewable = load_data(RENEWABLE_GROUPS_FILE) or {}
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Students sheet
        if students:
            df_students = pd.DataFrame(students)
            df_students.to_excel(writer, sheet_name='All Students', index=False)
        
        # Mechatronics groups
        if mechtronics:
            df_mech = generate_group_dataframes(mechtronics, 'Mechatronics')
            if not df_mech.empty:
                df_mech.to_excel(writer, sheet_name='Mechatronics Groups', index=False)
        
        # Renewable groups
        if renewable:
            df_renew = generate_group_dataframes(renewable, 'Renewable Energy')
            if not df_renew.empty:
                df_renew.to_excel(writer, sheet_name='Renewable Groups', index=False)
        
        # Statistics sheet
        stats_data = []
        if students:
            stats_data.append(['Total Students', len(students)])
            stats_data.append(['Mechatronics Groups', sum(len(g) for g in mechtronics.values())])
            stats_data.append(['Renewable Groups', sum(len(g) for g in renewable.values())])
            stats_data.append(['Generated', datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        
        if stats_data:
            df_stats = pd.DataFrame(stats_data, columns=['Metric', 'Value'])
            df_stats.to_excel(writer, sheet_name='Statistics', index=False)
    
    return output.getvalue()

# ==================== AUTHENTICATION ====================

def check_password():
    """Returns `True` if the user is authenticated"""
    def login_form():
        with st.form("Credentials"):
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.form_submit_button("Login", on_click=password_entered)
    
    def password_entered():
        if st.session_state["username"] == ADMIN_USERNAME and \
           hashlib.sha256(st.session_state["password"].encode()).hexdigest() == ADMIN_PASSWORD_HASH:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            del st.session_state["username"]
            log_operation("admin_login", {"username": ADMIN_USERNAME})
        else:
            st.session_state["password_correct"] = False
            log_operation("failed_login", {"username": st.session_state.get("username")})
    
    if st.session_state.get("password_correct", False):
        return True
    
    login_form()
    if "password_correct" in st.session_state:
        st.error("❌ Invalid username or password")
    return False

# ==================== STUDENT INTERFACE ====================

def student_interface():
    st.title("📝 Student Registration")
    st.markdown("Please fill in your details to register for Electrical Engineering Labs")
    
    # Create two columns for registration and status
    col1, col2 = st.columns([2, 1])
    
    with col1:
        with st.form("student_registration", clear_on_submit=True):
            st.subheader("Registration Form")
            
            name = st.text_input(
                "Full Name", 
                placeholder="Enter your full name",
                help="Use your official name as registered"
            )
            
            index = st.text_input(
                "Index Number", 
                placeholder="STUBTECH220457", 
                help="Format: STUBTECH followed by 6 digits"
            )
            
            submitted = st.form_submit_button("📝 Register", use_container_width=True, type="primary")
            
            if submitted:
                # Validations
                if not name or not index:
                    st.error("❌ Please fill in all fields")
                elif not validate_name(name):
                    st.error("❌ Please enter a valid name (letters, spaces, and basic punctuation only)")
                elif not validate_index_number(index):
                    st.error("❌ Invalid index number format. Use STUBTECH followed by 6 digits (e.g., STUBTECH220457)")
                else:
                    is_dup, dup_msg = is_duplicate_student(index.upper(), name)
                    if is_dup:
                        st.error(f"❌ {dup_msg}")
                    else:
                        # Save student
                        students = load_data(STUDENTS_FILE) or []
                        new_student = {
                            'name': name.strip(),
                            'index': index.upper(),
                            'registration_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        students.append(new_student)
                        save_data(STUDENTS_FILE, students)
                        
                        # Update groups if we have enough students
                        if len(students) >= 6:
                            reassign_groups_scalable()
                        
                        # Log registration
                        log_operation("student_registered", {
                            "index": index.upper(),
                            "total_students": len(students)
                        })
                        
                        st.success("✅ Registration successful!")
                        st.balloons()
                        st.rerun()
    
    with col2:
        # Show current stats
        students = load_data(STUDENTS_FILE) or []
        st.subheader("📊 Current Statistics")
        
        if students:
            st.metric("Total Registered", len(students))
            st.metric("Registration Date", datetime.now().strftime("%d %b %Y"))
            
            # Show recent registrations
            with st.expander("Recent Registrations"):
                recent = students[-5:] if len(students) > 5 else students
                for s in reversed(recent):
                    st.caption(f"• {s['name']} ({s['index']})")
        else:
            st.info("No students registered yet")
            st.caption("Be the first to register!")

# ==================== ADMIN INTERFACE ====================

def admin_interface():
    st.title("👨‍🏫 Admin Dashboard")
    
    # Sidebar for admin options
    admin_action = st.sidebar.selectbox(
        "📋 Admin Actions",
        ["Dashboard", "View Students", "Manage Groups", "Backup & Restore", "Generate Reports", "System Logs"]
    )
    
    # Show performance metrics in sidebar
    with st.sidebar.expander("📊 System Status", expanded=False):
        students = load_data(STUDENTS_FILE) or []
        st.metric("Total Students", len(students))
        
        metrics = get_performance_metrics()
        if metrics:
            st.write("**Recent Operations:**")
            for op, data in list(metrics.items())[:3]:
                st.caption(f"• {op}: {data['count']}x")
    
    # Route to appropriate function
    if admin_action == "Dashboard":
        show_admin_dashboard()
    elif admin_action == "View Students":
        manage_students_scalable()
    elif admin_action == "Manage Groups":
        manage_groups_scalable()
    elif admin_action == "Backup & Restore":
        backup_interface_scalable()
    elif admin_action == "Generate Reports":
        generate_reports_scalable()
    elif admin_action == "System Logs":
        show_system_logs()

def show_admin_dashboard():
    st.header("📊 Dashboard")
    
    # Load data
    students = load_data(STUDENTS_FILE) or []
    mechtronics = load_data(MECHTRONICS_GROUPS_FILE) or {}
    renewable = load_data(RENEWABLE_GROUPS_FILE) or {}
    app_state = load_data(APP_STATE_FILE) or {}
    
    # Key metrics row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "Total Students", 
            len(students),
            delta=f"{len(students)} registered"
        )
    
    with col2:
        total_mech = sum(len(g) for g in mechtronics.values())
        st.metric(
            "Mechatronics", 
            total_mech,
            delta=f"{total_mech/len(students)*100:.0f}%" if students else "0%"
        )
    
    with col3:
        total_renew = sum(len(g) for g in renewable.values())
        st.metric(
            "Renewable", 
            total_renew,
            delta=f"{total_renew/len(students)*100:.0f}%" if students else "0%"
        )
    
    with col4:
        last_backup = app_state.get('last_backup', 'Never')
        if last_backup != 'Never':
            last_backup = last_backup.replace('_', ' at ')
        st.metric("Last Backup", last_backup)
    
    with col5:
        last_grouping = app_state.get('last_grouping', 'Never')
        if last_grouping != 'Never':
            last_grouping = last_grouping[:10]  # Just show date
        st.metric("Last Grouping", last_grouping)
    
    # Show group statistics
    if students:
        show_group_statistics()
    else:
        st.info("No students registered yet. Groups will be created once students register.")
    
    # Quick actions
    st.markdown("---")
    st.subheader("⚡ Quick Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🔄 Reassign Groups", use_container_width=True, type="primary"):
            with st.spinner("Reassigning groups..."):
                success, message = reassign_groups_scalable()
                if success:
                    st.success(message)
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning(message)
    
    with col2:
        if st.button("💾 Create Backup", use_container_width=True):
            timestamp, zip_path = create_backup()
            st.success(f"Backup created: {timestamp}")
    
    with col3:
        if st.button("📥 Export All Data", use_container_width=True):
            excel_data = export_all_data()
            b64 = base64.b64encode(excel_data).decode()
            href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="lab_grouping_export.xlsx">Click here to download</a>'
            st.markdown(href, unsafe_allow_html=True)
    
    with col4:
        if st.button("🧹 Clear Cache", use_container_width=True):
            st.cache_data.clear()
            st.success("Cache cleared!")

def manage_students_scalable():
    """Enhanced student management with pagination and batch operations"""
    st.header("📋 Student Management")
    
    students = load_data(STUDENTS_FILE) or []
    
    if not students:
        st.info("No students registered yet")
        return
    
    # Search and filter
    col1, col2 = st.columns([3, 1])
    
    with col1:
        search = st.text_input("🔍 Search students by name or index", placeholder="Type to search...")
    
    with col2:
        sort_by = st.selectbox("Sort by", ["Name", "Index", "Date"])
    
    # Convert to DataFrame
    df = pd.DataFrame(students)
    
    # Apply search
    if search:
        mask = df['name'].str.contains(search, case=False, na=False) | \
               df['index'].str.contains(search, case=False, na=False)
        df = df[mask]
    
    # Apply sorting
    if sort_by == "Name":
        df = df.sort_values('name')
    elif sort_by == "Index":
        df = df.sort_values('index')
    elif sort_by == "Date":
        df = df.sort_values('registration_date', ascending=False)
    
    # Show statistics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Students", len(students))
    with col2:
        st.metric("Showing", len(df))
    with col3:
        st.metric("Pages", (len(df) + PAGE_SIZE - 1) // PAGE_SIZE)
    
    # Paginate
    df_paginated = paginate_dataframe(df)
    
    # Display dataframe
    st.dataframe(
        df_paginated,
        use_container_width=True,
        column_config={
            "name": "Student Name",
            "index": "Index Number",
            "registration_date": "Registration Date"
        },
        hide_index=True
    )
    
    # Batch operations
    with st.expander("⚡ Batch Operations"):
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📤 Export Visible Students", use_container_width=True):
                csv = df_paginated.to_csv(index=False)
                b64 = base64.b64encode(csv.encode()).decode()
                href = f'<a href="data:file/csv;base64,{b64}" download="students_export.csv">Download CSV</a>'
                st.markdown(href, unsafe_allow_html=True)
        
        with col2:
            if st.button("🗑️ Delete All Students", use_container_width=True, type="secondary"):
                if st.checkbox("I understand this cannot be undone"):
                    if st.button("Confirm Delete All"):
                        save_data(STUDENTS_FILE, [])
                        st.success("All students deleted!")
                        st.rerun()
    
    # Individual student deletion
    with st.expander("🗑️ Delete Individual Student"):
        student_to_delete = st.selectbox(
            "Select student to delete",
            options=[f"{s['index']} - {s['name']}" for s in students],
            key="delete_select"
        )
        
        if st.button("Delete Selected Student", type="secondary"):
            idx = [f"{s['index']} - {s['name']}" for s in students].index(student_to_delete)
            deleted = students.pop(idx)
            save_data(STUDENTS_FILE, students)
            reassign_groups_scalable()
            st.success(f"Deleted {deleted['name']}")
            log_operation("student_deleted", {"index": deleted['index']})
            st.rerun()

def manage_groups_scalable():
    """Enhanced group management with better visualization"""
    st.header("👥 Group Management")
    
    students = load_data(STUDENTS_FILE) or []
    mechtronics = load_data(MECHTRONICS_GROUPS_FILE) or {}
    renewable = load_data(RENEWABLE_GROUPS_FILE) or {}
    
    if not students:
        st.info("No students registered yet")
        return
    
    # Group overview
    st.subheader("📊 Group Overview")
    
    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(["Mechatronics Lab", "Renewable Energy Lab", "Comparison"])
    
    with tab1:
        st.markdown("### 🔧 Mechatronics Lab Groups")
        
        col1, col2 = st.columns(2)
        
        for idx, (group_name, members) in enumerate(mechtronics.items()):
            with col1 if idx == 0 else col2:
                with st.expander(f"{group_name} ({len(members)} students)", expanded=True):
                    if members:
                        df = pd.DataFrame(members)
                        df_display = df[['index', 'name']].copy()
                        
                        # Paginate if needed
                        if len(df_display) > 20:
                            df_display = df_display.head(20)
                            st.caption(f"Showing first 20 of {len(members)} students")
                        
                        st.dataframe(df_display, use_container_width=True, hide_index=True)
                        
                        # Export option
                        if st.button(f"📥 Export {group_name}", key=f"export_mech_{group_name}"):
                            csv = df[['index', 'name']].to_csv(index=False)
                            b64 = base64.b64encode(csv.encode()).decode()
                            href = f'<a href="data:file/csv;base64,{b64}" download="{group_name}_mechatronics.csv">Download CSV</a>'
                            st.markdown(href, unsafe_allow_html=True)
                    else:
                        st.write("No students in this group")
    
    with tab2:
        st.markdown("### 🌱 Renewable Energy Lab Groups")
        
        cols = st.columns(3)
        
        for idx, (group_name, members) in enumerate(renewable.items()):
            with cols[idx]:
                with st.expander(f"{group_name} ({len(members)} students)", expanded=True):
                    if members:
                        df = pd.DataFrame(members)
                        df_display = df[['index', 'name']].copy()
                        
                        # Paginate if needed
                        if len(df_display) > 15:
                            df_display = df_display.head(15)
                            st.caption(f"Showing first 15 of {len(members)} students")
                        
                        st.dataframe(df_display, use_container_width=True, hide_index=True)
                        
                        # Export option
                        if st.button(f"📥 Export {group_name}", key=f"export_renew_{group_name}"):
                            csv = df[['index', 'name']].to_csv(index=False)
                            b64 = base64.b64encode(csv.encode()).decode()
                            href = f'<a href="data:file/csv;base64,{b64}" download="{group_name}_renewable.csv">Download CSV</a>'
                            st.markdown(href, unsafe_allow_html=True)
                    else:
                        st.write("No students in this group")
    
    with tab3:
        st.markdown("### 📈 Group Comparison")
        
        # Prepare comparison data
        comparison_data = []
        
        for group_name, members in mechtronics.items():
            comparison_data.append({
                'Lab': 'Mechatronics',
                'Group': group_name,
                'Students': len(members),
                'Percentage': f"{len(members)/len(students)*100:.1f}%"
            })
        
        for group_name, members in renewable.items():
            comparison_data.append({
                'Lab': 'Renewable',
                'Group': group_name,
                'Students': len(members),
                'Percentage': f"{len(members)/len(students)*100:.1f}%"
            })
        
        if comparison_data:
            df_comp = pd.DataFrame(comparison_data)
            
            # Create visualization
            fig = px.bar(
                df_comp,
                x='Group',
                y='Students',
                color='Lab',
                text='Students',
                barmode='group',
                title='Group Size Comparison'
            )
            fig.update_traces(texttemplate='%{text}', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)
            
            # Show as table
            st.dataframe(df_comp, use_container_width=True, hide_index=True)
    
    # Group controls
    st.markdown("---")
    st.subheader("🔄 Group Controls")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Reassign All Groups", use_container_width=True, type="primary"):
            with st.spinner("Reassigning groups..."):
                success, message = reassign_groups_scalable()
                if success:
                    st.success(message)
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning(message)
    
    with col2:
        if st.button("📊 View Distribution", use_container_width=True):
            show_group_statistics()
    
    with col3:
        if st.button("📥 Export All Groups", use_container_width=True):
            # Create combined export
            mech_df = generate_group_dataframes(mechtronics, 'Mechatronics')
            renew_df = generate_group_dataframes(renewable, 'Renewable Energy')
            
            if not mech_df.empty and not renew_df.empty:
                combined_df = pd.concat([mech_df, renew_df], ignore_index=True)
                excel_data = to_excel(combined_df)
                b64 = base64.b64encode(excel_data).decode()
                href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="all_groups.xlsx">Click here to download</a>'
                st.markdown(href, unsafe_allow_html=True)

def backup_interface_scalable():
    """Enhanced backup interface with better management"""
    st.header("💾 Backup & Restore")
    
    tab1, tab2 = st.tabs(["Create Backup", "Restore Backup"])
    
    with tab1:
        st.subheader("Create New Backup")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📀 Create Backup Now", type="primary", use_container_width=True):
                with st.spinner("Creating backup..."):
                    timestamp, zip_path = create_backup()
                    st.success(f"✅ Backup created successfully!")
                    st.info(f"Backup ID: {timestamp}")
                    
                    # Provide download link
                    with open(zip_path, 'rb') as f:
                        zip_data = f.read()
                    b64 = base64.b64encode(zip_data).decode()
                    href = f'<a href="data:application/zip;base64,{b64}" download="backup_{timestamp}.zip">📥 Download Backup ZIP</a>'
                    st.markdown(href, unsafe_allow_html=True)
        
        with col2:
            if st.button("🔄 Auto-Backup Now", use_container_width=True):
                students = load_data(STUDENTS_FILE) or []
                if len(students) % 10 == 0:  # Simulate auto-backup condition
                    timestamp, zip_path = create_backup()
                    st.success(f"Auto-backup created: {timestamp}")
                else:
                    st.info("No auto-backup triggered. Auto-backups occur every 10 new students.")
        
        # List recent backups
        st.subheader("Recent Backups")
        backups = list_backups()[:5]
        
        if backups:
            for backup in backups:
                with st.expander(f"📁 {backup['name']}"):
                    st.write(f"**Timestamp:** {backup['timestamp']}")
                    st.write(f"**Size:** {backup['size']}")
                    
                    # List files in backup
                    files = os.listdir(backup['path'])
                    st.write("**Files included:**")
                    for file in files:
                        st.caption(f"  • {file}")
        else:
            st.info("No backups available")
    
    with tab2:
        st.subheader("Restore from Backup")
        
        backups = list_backups()
        
        if backups:
            backup_options = [f"{b['name']} ({b['timestamp']})" for b in backups]
            selected = st.selectbox("Select backup to restore", backup_options)
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔄 Preview Backup", use_container_width=True):
                    idx = backup_options.index(selected)
                    backup = backups[idx]
                    
                    st.write(f"**Backup Details:**")
                    st.write(f"- Created: {backup['timestamp']}")
                    st.write(f"- Size: {backup['size']}")
                    
                    # Show files
                    files = os.listdir(backup['path'])
                    st.write("**Files:**")
                    for file in files:
                        st.caption(f"  • {file}")
            
            with col2:
                if st.button("⚠️ Restore Backup", use_container_width=True, type="secondary"):
                    if st.checkbox("I understand this will overwrite current data"):
                        idx = backup_options.index(selected)
                        with st.spinner("Restoring backup..."):
                            if restore_from_backup(backups[idx]['path']):
                                st.success("✅ Backup restored successfully!")
                                st.rerun()
                            else:
                                st.error("❌ Failed to restore backup")
        else:
            st.info("No backups available to restore")

def generate_reports_scalable():
    """Enhanced report generation with multiple options"""
    st.header("📑 Generate Reports")
    
    students = load_data(STUDENTS_FILE) or []
    mechtronics = load_data(MECHTRONICS_GROUPS_FILE) or {}
    renewable = load_data(RENEWABLE_GROUPS_FILE) or {}
    
    if not students:
        st.info("No students registered yet")
        return
    
    report_type = st.radio(
        "Select Report Type",
        ["Mechatronics Lab", "Renewable Energy Lab", "Combined Report", "Complete Export"],
        horizontal=True
    )
    
    if report_type == "Mechatronics Lab":
        df = generate_group_dataframes(mechtronics, "Mechatronics")
        if not df.empty:
            st.subheader(f"Mechatronics Lab Groups ({len(df)} students)")
            
            # Add marks column for editing
            df['Marks'] = ''
            
            # Display with editor
            edited_df = st.data_editor(
                df,
                use_container_width=True,
                column_config={
                    "index": "Index Number",
                    "name": "Student Name",
                    "Group": "Group",
                    "Lab": "Lab",
                    "Marks": st.column_config.NumberColumn("Marks", min_value=0, max_value=100)
                },
                disabled=["index", "name", "Group", "Lab"],
                hide_index=True
            )
            
            # Download options
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(get_download_link(df, "mechatronics_groups", "📥 Download as Excel"), unsafe_allow_html=True)
            with col2:
                # CSV download
                csv = df.to_csv(index=False)
                b64 = base64.b64encode(csv.encode()).decode()
                href = f'<a href="data:file/csv;base64,{b64}" download="mechatronics_groups.csv">📥 Download as CSV</a>'
                st.markdown(href, unsafe_allow_html=True)
            
            # Save marks
            if st.button("💾 Save Marks", type="primary"):
                # Update marks in the original data
                for _, row in edited_df.iterrows():
                    for group in mechtronics.values():
                        for student in group:
                            if student['index'] == row['index']:
                                student['marks'] = row['Marks']
                save_data(MECHTRONICS_GROUPS_FILE, mechtronics)
                st.success("Marks saved successfully!")
        else:
            st.info("No Mechatronics group data available")
    
    elif report_type == "Renewable Energy Lab":
        df = generate_group_dataframes(renewable, "Renewable Energy")
        if not df.empty:
            st.subheader(f"Renewable Energy Lab Groups ({len(df)} students)")
            
            # Add marks column
            df['Marks'] = ''
            
            # Display with editor
            edited_df = st.data_editor(
                df,
                use_container_width=True,
                column_config={
                    "index": "Index Number",
                    "name": "Student Name",
                    "Group": "Group",
                    "Lab": "Lab",
                    "Marks": st.column_config.NumberColumn("Marks", min_value=0, max_value=100)
                },
                disabled=["index", "name", "Group", "Lab"],
                hide_index=True
            )
            
            # Download options
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(get_download_link(df, "renewable_groups", "📥 Download as Excel"), unsafe_allow_html=True)
            with col2:
                csv = df.to_csv(index=False)
                b64 = base64.b64encode(csv.encode()).decode()
                href = f'<a href="data:file/csv;base64,{b64}" download="renewable_groups.csv">📥 Download as CSV</a>'
                st.markdown(href, unsafe_allow_html=True)
            
            # Save marks
            if st.button("💾 Save Marks", type="primary"):
                for _, row in edited_df.iterrows():
                    for group in renewable.values():
                        for student in group:
                            if student['index'] == row['index']:
                                student['marks'] = row['Marks']
                save_data(RENEWABLE_GROUPS_FILE, renewable)
                st.success("Marks saved successfully!")
        else:
            st.info("No Renewable Energy group data available")
    
    elif report_type == "Combined Report":
        df1 = generate_group_dataframes(mechtronics, "Mechatronics")
        df2 = generate_group_dataframes(renewable, "Renewable Energy")
        
        if not df1.empty and not df2.empty:
            combined_df = pd.concat([df1, df2], ignore_index=True)
            st.subheader(f"Combined Report ({len(combined_df)} students)")
            
            st.dataframe(combined_df, use_container_width=True, hide_index=True)
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(get_download_link(combined_df, "combined_groups", "📥 Download Combined as Excel"), unsafe_allow_html=True)
            with col2:
                csv = combined_df.to_csv(index=False)
                b64 = base64.b64encode(csv.encode()).decode()
                href = f'<a href="data:file/csv;base64,{b64}" download="combined_groups.csv">📥 Download Combined as CSV</a>'
                st.markdown(href, unsafe_allow_html=True)
        else:
            st.info("No group data available")
    
    else:  # Complete Export
        st.subheader("Complete Data Export")
        
        if st.button("📦 Generate Complete Export", type="primary"):
            excel_data = export_all_data()
            b64 = base64.b64encode(excel_data).decode()
            href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="complete_lab_export.xlsx">📥 Download Complete Export (Multi-sheet Excel)</a>'
            st.markdown(href, unsafe_allow_html=True)
            
            st.success("Export generated successfully!")

def show_system_logs():
    """Display system logs and performance metrics"""
    st.header("📋 System Logs")
    
    logs = load_data(LOG_FILE) or []
    
    if not logs:
        st.info("No logs available")
        return
    
    # Filter options
    col1, col2 = st.columns(2)
    
    with col1:
        operation_filter = st.multiselect(
            "Filter by Operation",
            options=list(set(log['operation'] for log in logs[-100:]))
        )
    
    with col2:
        date_range = st.date_input(
            "Date Range",
            value=(datetime.now().date(), datetime.now().date()),
            key="date_range"
        )
    
    # Apply filters
    filtered_logs = logs[-500:]  # Last 500 logs
    
    if operation_filter:
        filtered_logs = [log for log in filtered_logs if log['operation'] in operation_filter]
    
    # Convert to DataFrame
    df_logs = pd.DataFrame(filtered_logs)
    
    if not df_logs.empty:
        # Format timestamp
        df_logs['timestamp'] = pd.to_datetime(df_logs['timestamp'])
        df_logs['date'] = df_logs['timestamp'].dt.date
        df_logs['time'] = df_logs['timestamp'].dt.time
        
        # Display
        st.dataframe(
            df_logs[['date', 'time', 'operation', 'details']],
            use_container_width=True,
            column_config={
                "details": st.column_config.JsonColumn("Details")
            },
            hide_index=True
        )
        
        # Statistics
        st.subheader("📊 Operation Statistics")
        
        stats = df_logs['operation'].value_counts().reset_index()
        stats.columns = ['Operation', 'Count']
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.dataframe(stats, use_container_width=True, hide_index=True)
        
        with col2:
            fig = px.pie(stats, values='Count', names='Operation', title='Operation Distribution')
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No logs match the filters")

# ==================== MAIN APP ====================

def main():
    # Initialize
    init_directories()
    init_data_files()
    
    # Sidebar navigation
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/000000/electrical.png", width=80)
        st.title("EE Lab Grouping")
        
        st.markdown("---")
        
        if st.button("🎓 Student Portal", use_container_width=True, 
                    type="primary" if st.session_state.get('page') != "Student" else "secondary"):
            st.session_state.page = "Student"
            st.rerun()
        
        if st.button("👨‍🏫 Admin Portal", use_container_width=True,
                    type="primary" if st.session_state.get('page') == "Admin" else "secondary"):
            st.session_state.page = "Admin"
            st.rerun()
        
        st.markdown("---")
        
        # Show current stats in sidebar
        students = load_data(STUDENTS_FILE) or []
        st.metric("Total Students", len(students))
        
        if students:
            st.caption(f"Last registration: {students[-1].get('registration_date', 'N/A')[:10]}")
        
        st.markdown("---")
        st.caption("© 2024 Electrical Engineering")
        st.caption("v2.0 - Scalable Edition")
    
    # Page routing
    if st.session_state.get('page') == "Admin":
        if check_password():
            admin_interface()
    else:
        # Default to student interface
        st.session_state.page = "Student"
        student_interface()

if __name__ == "__main__":
    main()
