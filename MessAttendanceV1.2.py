import streamlit as st
import pandas as pd
import datetime
import sqlite3
import math
import hashlib

# --- CONFIGURATION & CONSTANTS ---
PRICES = {
    "Breakfast": 248.45,
    "Lunch": 480.32,
    "Dinner": 448.20
}
TAX_RATE = 0.05
SUBSIDY_RATE = 0.60

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("mess_tracker.db")
    cursor = conn.cursor()
    # Users table tracking P. No and hashed passwords
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            p_no TEXT PRIMARY KEY,
            password_hash TEXT
        )
    ''')
    # Meal logs linked via p_no
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS meal_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            p_no TEXT,
            date TEXT,
            meal_type TEXT,
            meal_category TEXT, -- 'Regular' or 'Extra'
            cost REAL
        )
    ''')
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

init_db()

# --- STREAMLIT UI SETUP ---
st.set_page_config(page_title="Company Mess Tracker", page_icon="🍲", layout="centered")
st.title("🍲 Company Mess Attendance Tracker")

# Initialize session state variables
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.p_no = ""

# --- LOGIN & REGISTRATION INTERFACE ---
if not st.session_state.logged_in:
    auth_tab = st.radio("Choose Action", ["Login", "Create Account Structure (Register)"], horizontal=True)
    
    if auth_tab == "Create Account Structure (Register)":
        st.subheader("📝 Register New Account")
        reg_p_no = st.text_input("Enter 4-Digit P. No:", max_chars=4, placeholder="e.g., 1234")
        reg_password = st.text_input("Set Password:", type="password", placeholder="Choose a secure password")
        reg_confirm = st.text_input("Confirm Password:", type="password", placeholder="Retype password")
        
        if st.button("Create Account", type="primary"):
            if len(reg_p_no) != 4 or not reg_p_no.isdigit():
                st.error("❌ P. No must be exactly a 4-digit number.")
            elif not reg_password:
                st.error("❌ Password field cannot be empty.")
            elif reg_password != reg_confirm:
                st.error("❌ Passwords do not match.")
            else:
                conn = sqlite3.connect("mess_tracker.db")
                cursor = conn.cursor()
                # Check if user already exists
                cursor.execute("SELECT p_no FROM users WHERE p_no = ?", (reg_p_no,))
                if cursor.fetchone():
                    st.error(f"❌ P. No {reg_p_no} is already registered. Please go to Login.")
                    conn.close()
                else:
                    # Save new user credentials safely using SHA-256 hashing
                    hashed = hash_password(reg_password)
                    cursor.execute("INSERT INTO users (p_no, password_hash) VALUES (?, ?)", (reg_p_no, hashed))
                    conn.commit()
                    conn.close()
                    st.success("🎉 Account created successfully! Please switch to 'Login' above to continue.")
                    
    elif auth_tab == "Login":
        st.subheader("🔑 Sign In")
        login_p_no = st.text_input("Enter 4-Digit P. No:", max_chars=4, placeholder="e.g., 1234")
        login_password = st.text_input("Enter Password:", type="password")
        
        if st.button("Sign In", type="primary"):
            conn = sqlite3.connect("mess_tracker.db")
            cursor = conn.cursor()
            cursor.execute("SELECT password_hash FROM users WHERE p_no = ?", (login_p_no,))
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0] == hash_password(login_password):
                st.session_state.logged_in = True
                st.session_state.p_no = login_p_no
                st.rerun()
            else:
                st.error("❌ Invalid P. No or Password. Please try again.")
                
    st.stop()  # Stop code execution here until user logs in successfully

# --- LOGGED IN USER SESSION ---
current_user_p_no = st.session_state.p_no
st.sidebar.write(f"Logged in as P. No: **{current_user_p_no}**")
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.p_no = ""
    st.rerun()

# --- MAIN APP INTERFACE ---
tabs = st.tabs(["📝 Log Daily Meals", "📊 Monthly Bills & Insights"])

# --- TAB 1: LOG MEALS ---
with tabs[0]:
    st.header("Mark Attendance")
    selected_date = st.date_input("Select Date", datetime.date.today())
    date_str = selected_date.strftime("%Y-%m-%d")
    
    st.divider()
    
    for meal in ["Breakfast", "Lunch", "Dinner"]:
        col1, col2, col3 = st.columns([2, 2, 3])
        
        with col1:
            st.write(f"**{meal}** (PKR {PRICES[meal]:.2f})")
            
        with col2:
            # Check if user has already marked this meal for the selected date
            conn = sqlite3.connect("mess_tracker.db")
            df_check = pd.read_sql_query(
                "SELECT meal_category FROM meal_logs WHERE p_no=? AND date=? AND meal_type=?", 
                conn, params=(current_user_p_no, date_str, meal)
            )
            conn.close()
            
            if not df_check.empty:
                current_status = df_check['meal_category'].values[0]
                st.success(f"Logged as {current_status}")
            else:
                st.info("Not Consumed")
                
        with col3:
            action = st.selectbox(f"Mark {meal}", ["Select...", "Regular (Subsidized)", "Extra (Out of pocket)", "Delete Entry"], key=f"select_{meal}")
            
            if action == "Regular (Subsidized)":
                conn = sqlite3.connect("mess_tracker.db")
                cursor = conn.cursor()
                cursor.execute("DELETE FROM meal_logs WHERE p_no=? AND date=? AND meal_type=?", (current_user_p_no, date_str, meal))
                cursor.execute("INSERT INTO meal_logs (p_no, date, meal_type, meal_category, cost) VALUES (?, ?, ?, ?, ?)",
                               (current_user_p_no, date_str, meal, "Regular", PRICES[meal]))
                conn.commit()
                conn.close()
                st.rerun()
                
            elif action == "Extra (Out of pocket)":
                conn = sqlite3.connect("mess_tracker.db")
                cursor = conn.cursor()
                cursor.execute("DELETE FROM meal_logs WHERE p_no=? AND date=? AND meal_type=?", (current_user_p_no, date_str, meal))
                cursor.execute("INSERT INTO meal_logs (p_no, date, meal_type, meal_category, cost) VALUES (?, ?, ?, ?, ?)",
                               (current_user_p_no, date_str, meal, "Extra", PRICES[meal]))
                conn.commit()
                conn.close()
                st.rerun()
                
            elif action == "Delete Entry":
                conn = sqlite3.connect("mess_tracker.db")
                cursor = conn.cursor()
                cursor.execute("DELETE FROM meal_logs WHERE p_no=? AND date=? AND meal_type=?", (current_user_p_no, date_str, meal))
                conn.commit()
                conn.close()
                st.rerun()

# --- TAB 2: BILLS & MATH CALCULATOR ---
with tabs[1]:
    st.header("Monthly Consumption & Bill Statement")
    
    current_year = datetime.date.today().year
    month_names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    selected_month_name = st.selectbox("Select Billing Month", month_names, index=datetime.date.today().month - 1)
    selected_month_num = month_names.index(selected_month_name) + 1
    
    conn = sqlite3.connect("mess_tracker.db")
    df = pd.read_sql_query("SELECT * FROM meal_logs WHERE p_no=?", conn, params=(current_user_p_no,))
    conn.close()
    
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df = df[(df['date'].dt.month == selected_month_num) & (df['date'].dt.year == current_year)]
        
    if df.empty:
        st.warning("No meals logged for this month yet.")
    else:
        df_regular = df[df['meal_category'] == 'Regular']
        df_extra = df[df['meal_category'] == 'Extra']
        
        # 1. Calculate Salary Deduction (Subsidized Regular Meals)
        base_regular_total = df_regular['cost'].sum()
        regular_tax = base_regular_total * TAX_RATE
        regular_subsidy = (base_regular_total + regular_tax) * SUBSIDY_RATE
        final_salary_deduction = math.ceil((base_regular_total + regular_tax) - regular_subsidy)
        
        # 2. Calculate Out of Pocket (Unsubsidized Extra Meals)
        base_extra_total = df_extra['cost'].sum()
        final_out_of_pocket = math.ceil(base_extra_total)
        
        st.subheader(f"Summary for {selected_month_name} {current_year}")
        
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            st.metric(label="Salary Deduction (Subsidized)", value=f"PKR {final_salary_deduction:,}")
            st.caption("Includes 5% Tax & 40% Subsidy (Rounded Up)")
            
        with col_b2:
            st.metric(label="Out of Pocket Bill (Extras)", value=f"PKR {final_out_of_pocket:,}")
            st.caption("Pay via Cash/Online (Rounded Up)")
            
        st.markdown("### Itemized Breakdown")
        st.dataframe(df[['date', 'meal_type', 'meal_category', 'cost']].rename(columns={
            'date': 'Date', 'meal_type': 'Meal', 'meal_category': 'Type', 'cost': 'Base Cost (PKR)'
        }), use_container_width=True)
