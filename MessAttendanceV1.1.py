import streamlit as st
import pandas as pd
import datetime
import sqlite3
import math

# --- CONFIGURATION & CONSTANTS ---
# Base prices in PKR
PRICES = {
    "Breakfast": 248.45,
    "Lunch": 480.32,
    "Dinner": 448.20
}
TAX_RATE = 0.05
SUBSIDY_RATE = 0.40

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("mess_tracker.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS meal_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT,
            date TEXT,
            meal_type TEXT,
            meal_category TEXT, -- 'Regular' or 'Extra'
            cost REAL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- SIMULATED GOOGLE LOGIN ---
# (In production, deploy with Streamlit Authenticator or Google OAuth)
st.set_page_config(page_title="Company Mess Tracker", page_icon="🍲", layout="centered")
st.title("🍲 Company Mess Attendance Tracker")

if 'user_logged_in' not in st.session_state:
    st.session_state.user_logged_in = False
    st.session_state.user_email = ""

if not st.session_state.user_logged_in:
    st.subheader("Login securely using your Company Google ID")
    email = st.text_input("Enter Google Email (Simulation):", placeholder="your.name@company.com")
    if st.button("Sign in with Google", type="primary"):
        if email:
            st.session_state.user_logged_in = True
            st.session_state.user_email = email
            st.rerun()
        else:
            st.error("Please enter a valid email.")
    st.stop()

# --- LOGGED IN USER SESSION ---
user_email = st.session_state.user_email
st.sidebar.write(f"Logged in as: **{user_email}**")
if st.sidebar.button("Logout"):
    st.session_state.user_logged_in = False
    st.rerun()

# --- MAIN APP INTERFACE ---
tabs = st.tabs(["📝 Log Daily Meals", "📊 Monthly Bills & Insights"])

# --- TAB 1: LOG MEALS ---
with tabs[0]:
    st.header("Mark Today's Attendance")
    selected_date = st.date_input("Select Date", datetime.date.today())
    date_str = selected_date.strftime("%Y-%m-%d")
    
    st.divider()
    
    # Render logging buttons for each meal type
    for meal in ["Breakfast", "Lunch", "Dinner"]:
        col1, col2, col3 = st.columns([2, 2, 3])
        
        with col1:
            st.write(f"**{meal}** (PKR {PRICES[meal]:.2f})")
            
        with col2:
            # Check if already logged
            conn = sqlite3.connect("mess_tracker.db")
            df_check = pd.read_sql_query(
                "SELECT meal_category FROM meal_logs WHERE user_email=? AND date=? AND meal_type=?", 
                conn, params=(user_email, date_str, meal)
            )
            conn.close()
            
            if not df_check.empty:
                st.success(f"Logged as {df_check['meal_category'].values[0]}")
            else:
                st.info("Not Consumed")
                
        with col3:
            # Dropdown choice for the type of meal consumed
            action = st.selectbox(f"Mark {meal}", ["Select...", "Regular (Subsidized)", "Extra (Out of pocket)", "Delete Entry"], key=f"select_{meal}")
            
            if action == "Regular (Subsidized)":
                conn = sqlite3.connect("mess_tracker.db")
                cursor = conn.cursor()
                cursor.execute("DELETE FROM meal_logs WHERE user_email=? AND date=? AND meal_type=?", (user_email, date_str, meal))
                cursor.execute("INSERT INTO meal_logs (user_email, date, meal_type, meal_category, cost) VALUES (?, ?, ?, ?, ?)",
                               (user_email, date_str, meal, "Regular", PRICES[meal]))
                conn.commit()
                conn.close()
                st.rerun()
                
            elif action == "Extra (Out of pocket)":
                conn = sqlite3.connect("mess_tracker.db")
                cursor = conn.cursor()
                cursor.execute("DELETE FROM meal_logs WHERE user_email=? AND date=? AND meal_type=?", (user_email, date_str, meal))
                cursor.execute("INSERT INTO meal_logs (user_email, date, meal_type, meal_category, cost) VALUES (?, ?, ?, ?, ?)",
                               (user_email, date_str, meal, "Extra", PRICES[meal]))
                conn.commit()
                conn.close()
                st.rerun()
                
            elif action == "Delete Entry":
                conn = sqlite3.connect("mess_tracker.db")
                cursor = conn.cursor()
                cursor.execute("DELETE FROM meal_logs WHERE user_email=? AND date=? AND meal_type=?", (user_email, date_str, meal))
                conn.commit()
                conn.close()
                st.rerun()

# --- TAB 2: BILLS & MATH CALCULATOR ---
with tabs[1]:
    st.header("Monthly Consumption & Bill Statement")
    
    # Filter by Month
    current_year = datetime.date.today().year
    month_names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    selected_month_name = st.selectbox("Select Billing Month", month_names, index=datetime.date.today().month - 1)
    selected_month_num = month_names.index(selected_month_name) + 1
    
    # Load data from DB for this user and month
    conn = sqlite3.connect("mess_tracker.db")
    df = pd.read_sql_query("SELECT * FROM meal_logs WHERE user_email=?", conn, params=(user_email,))
    conn.close()
    
    if not df.empty:
        # Filter dataframe by month and year
        df['date'] = pd.to_datetime(df['date'])
        df = df[(df['date'].dt.month == selected_month_num) & (df['date'].dt.year == current_year)]
        
    if df.empty:
        st.warning("No meals logged for this month yet.")
    else:
        # Separate Regular vs Extras
        df_regular = df[df['meal_category'] == 'Regular']
        df_extra = df[df['meal_category'] == 'Extra']
        
        # Calculate Math
        base_regular_total = df_regular['cost'].sum()
        regular_tax = base_regular_total * TAX_RATE
        regular_subsidy = (base_regular_total + regular_tax) * SUBSIDY_RATE
        final_salary_deduction = math.ceil((base_regular_total + regular_tax) - regular_subsidy)
        
        base_extra_total = df_extra['cost'].sum()
        final_out_of_pocket = math.ceil(base_extra_total) # No tax or subsidy explicitly mentioned for extras
        
        # Display Totals
        st.subheader(f"Summary for {selected_month_name} {current_year}")
        
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            st.metric(label="Salary Deduction (Subsidized Bill)", value=f"PKR {final_salary_deduction:,}")
            st.caption("Includes 5% Tax & 40% Company Subsidy (Rounded Up)")
            
        with col_b2:
            st.metric(label="Out of Pocket Bill (Extras)", value=f"PKR {final_out_of_pocket:,}")
            st.caption("To be paid individually (Rounded Up)")
            
        # Detailed Breakdown Table
        st.markdown("### Itemized Breakdown")
        st.dataframe(df[['date', 'meal_type', 'meal_category', 'cost']].rename(columns={
            'date': 'Date', 'meal_type': 'Meal', 'meal_category': 'Type', 'cost': 'Base Cost (PKR)'
        }), use_container_width=True)