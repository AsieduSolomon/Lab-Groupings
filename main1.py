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
import re
import zipfile

# ==================== CONFIGURATION ====================
st.set_page_config(
    page_title="EE Lab Grouping System",
    page_icon="🔌",
    initial_sidebar_state="expanded",
    layout="wide"
)

# ==================== CONSTANTS ====================
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = hashlib.sha256("admin123".encode()).hexdigest()
DATA_DIR = "data"
BACKUP_DIR = "backups"
STUDENTS_FILE = os.path.join(DATA_DIR, "students.json")
MECHTRONICS_GROUPS_FILE = os.path.join(DATA_DIR, "mechtronics_groups.json")
RENEWABLE_GROUPS_FILE = os.path.join(DATA_DIR, "renewable_groups.json")
APP_STATE_FILE = os.path.join(DATA_DIR, "app_state.json")

# Pagination
PAGE_SIZE = 50

# ==================== INITIALIZATION ====================
def init_directories():
    """Create necessary directories"""
    for directory in [DATA_DIR, BACKUP_DIR]:
        if not os.path.exists(directory):
            os.makedirs(directory)

def init_data_files():
    """Initialize JSON files"""
    files_config = {
        STUDENTS_FILE: [],
        MECHTRONICS_GROUPS_FILE: {"Group A": [], "Group B": []},
        RENEWABLE_GROUPS_FILE: {"Group A": [], "Group B": [], "Group C": []},
        APP_STATE_FILE: {"last_backup": None, "total_students": 0}
    }
    
    for file_path, default_data in files_config.items():
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                json.dump(default_data, f)

# ==================== DATA MANAGEMENT ====================
def load_data(file_path):
    """Load data from JSON"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except:
        return None

def save_data(file_path, data):
    """Save data to JSON"""
    with open(file_path, 'w') as f:
        json.dump(data, f)

def create_backup():
    """Create a backup"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(BACKUP_DIR, f"backup_{timestamp}")
    os.makedirs(backup_dir, exist_ok=True)
    
    # Copy all JSON files
    for file in os.listdir(DATA_DIR):
        if file.endswith('.json'):
            src = os.path.join(DATA_DIR, file)
            dst = os.path.join(backup_dir, file)
            shutil.copy2(src, dst)
    
    # Update app state
    app_state = load_data(APP_STATE_FILE) or {}
    app_state['last_backup'] = timestamp
    save_data(APP_STATE_FILE, app_state)
    
    return timestamp

def list_backups():
    """List all backups"""
    if not os.path.exists(BACKUP_DIR):
        return []
    
    backups = []
    for item in os.listdir(BACKUP_DIR):
        if os.path.isdir(os.path.join(BACKUP_DIR, item)) and item.startswith('backup_'):
            backups.append({
                'name': item,
                'path': os.path.join(BACKUP_DIR, item),
                'timestamp': item.replace('backup_', '')
            })
    return sorted(backups, key=lambda x: x['timestamp'], reverse=True)

# ==================== VALIDATION ====================
def validate_index(index):
    """Validate index number"""
    pattern = r'^STUBTECH\d{6}$'
    return re.match(pattern, index.upper()) is not None

def validate_name(name):
    """Validate name"""
    return len(name.strip()) >= 2 and all(c.isalpha() or c.isspace() for c in name)

def is_duplicate(index):
    """Check for duplicate index"""
    students = load_data(STUDENTS_FILE) or []
    return any(s['index'] == index.upper() for s in students)

# ==================== GROUPING FUNCTIONS ====================
def assign_groups(students):
    """Assign students to groups"""
    if len(students) < 6:
        return False
    
    # Shuffle students
    shuffled = random.sample(students, len(students))
    
    # Mechatronics groups (2 groups)
    mech_groups = {"Group A": [], "Group B": []}
    for i, student in enumerate(shuffled):
        group = "Group A" if i % 2 == 0 else "Group B"
        mech_groups[group].append({
            **student,
            'marks': ''
        })
    
    # Renewable groups (3 groups)
    renew_groups = {"Group A": [], "Group B": [], "Group C": []}
    for i, student in enumerate(shuffled):
        if i % 3 == 0:
            group = "Group A"
        elif i % 3 == 1:
            group = "Group B"
        else:
            group = "Group C"
        renew_groups[group].append({
            **student,
            'marks': ''
        })
    
    # Save groups
    save_data(MECHTRONICS_GROUPS_FILE, mech_groups)
    save_data(RENEWABLE_GROUPS_FILE, renew_groups)
    
    return True

# ==================== EXCEL GENERATION ====================
def to_excel(df):
    """Convert to Excel"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# ==================== AUTHENTICATION ====================
def check_password():
    """Check admin password"""
    if st.session_state.get("authenticated", False):
        return True
    
    with st.form("login"):
        st.text_input("Username", key="username")
        st.text_input("Password", type="password", key="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            if st.session_state.username == ADMIN_USERNAME and \
               hashlib.sha256(st.session_state.password.encode()).hexdigest() == ADMIN_PASSWORD_HASH:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Invalid credentials")
    return False

# ==================== STUDENT INTERFACE ====================
def student_interface():
    st.title("📝 Student Registration")
    st.markdown("Register for Electrical Engineering Labs")
    
    with st.form("registration"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Full Name", placeholder="Enter your full name")
        
        with col2:
            index = st.text_input("Index Number", placeholder="STUBTECH220457")
        
        submitted = st.form_submit_button("Register", type="primary")
        
        if submitted:
            if not name or not index:
                st.error("Please fill all fields")
            elif not validate_name(name):
                st.error("Invalid name")
            elif not validate_index(index):
                st.error("Invalid index format. Use STUBTECH followed by 6 digits")
            elif is_duplicate(index):
                st.error("Index number already registered")
            else:
                # Save student
                students = load_data(STUDENTS_FILE) or []
                students.append({
                    'name': name.strip(),
                    'index': index.upper(),
                    'date': datetime.now().strftime("%Y-%m-%d")
                })
                save_data(STUDENTS_FILE, students)
                
                # Update groups
                if len(students) >= 6:
                    assign_groups(students)
                
                st.success("Registration successful!")
                st.balloons()
                st.rerun()
    
    # Show stats
    students = load_data(STUDENTS_FILE) or []
    if students:
        st.divider()
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Students", len(students))
        col2.metric("Mechatronics Groups", "2")
        col3.metric("Renewable Groups", "3")

# ==================== ADMIN INTERFACE ====================
def admin_interface():
    st.title("👨‍🏫 Admin Dashboard")
    
    # Sidebar
    menu = st.sidebar.radio(
        "Menu",
        ["Dashboard", "Students", "Groups", "Reports", "Backup"]
    )
    
    if menu == "Dashboard":
        show_dashboard()
    elif menu == "Students":
        manage_students()
    elif menu == "Groups":
        view_groups()
    elif menu == "Reports":
        generate_reports()
    elif menu == "Backup":
        backup_interface()

def show_dashboard():
    """Show dashboard"""
    students = load_data(STUDENTS_FILE) or []
    mech = load_data(MECHTRONICS_GROUPS_FILE) or {}
    renew = load_data(RENEWABLE_GROUPS_FILE) or {}
    app_state = load_data(APP_STATE_FILE) or {}
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Students", len(students))
    col2.metric("Mechatronics", sum(len(g) for g in mech.values()))
    col3.metric("Renewable", sum(len(g) for g in renew.values()))
    col4.metric("Last Backup", app_state.get('last_backup', 'Never')[:10] if app_state.get('last_backup') else 'Never')
    
    # Charts
    if students:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Mechatronics Groups")
            if mech:
                data = {'Group': list(mech.keys()), 'Count': [len(v) for v in mech.values()]}
                df = pd.DataFrame(data)
                fig = px.bar(df, x='Group', y='Count', title='Group Distribution')
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Renewable Groups")
            if renew:
                data = {'Group': list(renew.keys()), 'Count': [len(v) for v in renew.values()]}
                df = pd.DataFrame(data)
                fig = px.bar(df, x='Group', y='Count', title='Group Distribution')
                st.plotly_chart(fig, use_container_width=True)

def manage_students():
    """Manage students"""
    st.header("Student Management")
    
    students = load_data(STUDENTS_FILE) or []
    
    if not students:
        st.info("No students registered")
        return
    
    # Search
    search = st.text_input("🔍 Search", placeholder="Name or Index")
    
    df = pd.DataFrame(students)
    
    if search:
        mask = df['name'].str.contains(search, case=False) | df['index'].str.contains(search, case=False)
        df = df[mask]
    
    # Pagination
    total_pages = (len(df) + PAGE_SIZE - 1) // PAGE_SIZE
    page = st.number_input("Page", min_value=1, max_value=total_pages, value=1)
    
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    
    st.dataframe(df.iloc[start:end], use_container_width=True, hide_index=True)
    
    # Delete option
    with st.expander("Delete Student"):
        index_to_delete = st.selectbox("Select student", [f"{row['index']} - {row['name']}" for _, row in df.iterrows()])
        if st.button("Delete", type="secondary"):
            idx = [f"{s['index']} - {s['name']}" for s in students].index(index_to_delete)
            students.pop(idx)
            save_data(STUDENTS_FILE, students)
            assign_groups(students)  # Reassign groups
            st.success("Student deleted")
            st.rerun()

def view_groups():
    """View groups"""
    st.header("Group Management")
    
    mech = load_data(MECHTRONICS_GROUPS_FILE) or {}
    renew = load_data(RENEWABLE_GROUPS_FILE) or {}
    
    tab1, tab2 = st.tabs(["Mechatronics", "Renewable Energy"])
    
    with tab1:
        st.subheader("Mechatronics Lab Groups")
        col1, col2 = st.columns(2)
        
        for i, (group, members) in enumerate(mech.items()):
            with col1 if i == 0 else col2:
                with st.expander(f"{group} ({len(members)} students)"):
                    if members:
                        df = pd.DataFrame(members)
                        st.dataframe(df[['index', 'name']], use_container_width=True, hide_index=True)
    
    with tab2:
        st.subheader("Renewable Energy Groups")
        cols = st.columns(3)
        
        for i, (group, members) in enumerate(renew.items()):
            with cols[i]:
                with st.expander(f"{group} ({len(members)} students)"):
                    if members:
                        df = pd.DataFrame(members)
                        st.dataframe(df[['index', 'name']], use_container_width=True, hide_index=True)
    
    # Reassign button
    if st.button("🔄 Reassign Groups", type="primary"):
        students = load_data(STUDENTS_FILE) or []
        if assign_groups(students):
            st.success("Groups reassigned successfully")
            st.rerun()
        else:
            st.warning("Need at least 6 students")

def generate_reports():
    """Generate reports"""
    st.header("Generate Reports")
    
    mech = load_data(MECHTRONICS_GROUPS_FILE) or {}
    renew = load_data(RENEWABLE_GROUPS_FILE) or {}
    
    report_type = st.radio("Report Type", ["Mechatronics", "Renewable", "Combined"], horizontal=True)
    
    if report_type == "Mechatronics":
        if mech:
            data = []
            for group, members in mech.items():
                for m in members:
                    data.append({
                        'Index': m['index'],
                        'Name': m['name'],
                        'Group': group,
                        'Marks': ''
                    })
            df = pd.DataFrame(data)
            st.data_editor(df, use_container_width=True, hide_index=True)
            
            # Download
            excel_data = to_excel(df)
            b64 = base64.b64encode(excel_data).decode()
            st.markdown(f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="mechatronics_groups.xlsx">📥 Download Excel</a>', unsafe_allow_html=True)
    
    elif report_type == "Renewable":
        if renew:
            data = []
            for group, members in renew.items():
                for m in members:
                    data.append({
                        'Index': m['index'],
                        'Name': m['name'],
                        'Group': group,
                        'Marks': ''
                    })
            df = pd.DataFrame(data)
            st.data_editor(df, use_container_width=True, hide_index=True)
            
            # Download
            excel_data = to_excel(df)
            b64 = base64.b64encode(excel_data).decode()
            st.markdown(f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="renewable_groups.xlsx">📥 Download Excel</a>', unsafe_allow_html=True)
    
    else:  # Combined
        data = []
        for group, members in mech.items():
            for m in members:
                data.append({
                    'Index': m['index'],
                    'Name': m['name'],
                    'Lab': 'Mechatronics',
                    'Group': group,
                    'Marks': ''
                })
        for group, members in renew.items():
            for m in members:
                data.append({
                    'Index': m['index'],
                    'Name': m['name'],
                    'Lab': 'Renewable',
                    'Group': group,
                    'Marks': ''
                })
        
        if data:
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Download
            excel_data = to_excel(df)
            b64 = base64.b64encode(excel_data).decode()
            st.markdown(f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="all_groups.xlsx">📥 Download Excel</a>', unsafe_allow_html=True)

def backup_interface():
    """Backup interface"""
    st.header("Backup & Restore")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Create Backup")
        if st.button("Create Backup", type="primary"):
            timestamp = create_backup()
            st.success(f"Backup created: {timestamp}")
    
    with col2:
        st.subheader("Restore Backup")
        backups = list_backups()
        
        if backups:
            selected = st.selectbox("Select backup", [b['name'] for b in backups])
            if st.button("Restore"):
                st.warning("Restore functionality would go here")
        else:
            st.info("No backups available")

# ==================== MAIN ====================
def main():
    # Initialize
    init_directories()
    init_data_files()
    
    # Sidebar
    with st.sidebar:
        st.title("Navigation")
        if st.button("🎓 Student", use_container_width=True):
            st.session_state.page = "student"
        if st.button("👨‍🏫 Admin", use_container_width=True):
            st.session_state.page = "admin"
    
    # Page routing
    if st.session_state.get('page') == "admin":
        if check_password():
            admin_interface()
    else:
        student_interface()

if __name__ == "__main__":
    main()
