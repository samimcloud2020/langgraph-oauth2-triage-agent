import os
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="BSNL Trouble Ticket Solving Agent",
    page_icon="📶",
    layout="wide"
)

st.markdown("""
    <style>
    .stApp {
        background-color: #f8fafc;
        color: #0f172a;
        font-family: system-ui, -apple-system, sans-serif;
    }
    .bsnl-header {
        background-color: #003366;
        padding: 20px 24px;
        border-radius: 8px;
        border-left: 8px solid #ff9900;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
        margin-bottom: 24px;
    }
    .bsnl-title {
        color: #ffffff !important;
        font-size: 1.8rem !important;
        font-weight: 900 !important;
        margin: 0 !important;
    }
    .bsnl-subtitle {
        color: #e2e8f0 !important;
        font-size: 0.95rem !important;
        margin-top: 4px !important;
        font-weight: 700 !important;
    }
    .stTextInput > div > div > input {
        background-color: #ffffff !important;
        color: #003366 !important;
        border: 3px solid #003366 !important;
        border-radius: 8px !important;
        font-weight: 800 !important;
        font-size: 1.05rem !important;
        padding: 12px !important;
    }
    </style>
""", unsafe_allow_html=True)

if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "username" not in st.session_state:
    st.session_state.username = None
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "default_thread_id" not in st.session_state:
    st.session_state.default_thread_id = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

def handle_submit():
    user_msg = st.session_state.user_input_text.strip()
    if not user_msg:
        return
        
    st.session_state.chat_history.append({"role": "user", "content": f"**{user_msg}**"})
    
    headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
    payload = {
        "message": user_msg,
        "thread_id": st.session_state.default_thread_id,
        "username": st.session_state.get("username", "Customer")
    }

    try:
        res = requests.post(
            f"{API_BASE_URL}/triage", 
            json=payload, 
            headers=headers,
            timeout=30
        )
        
        if res.status_code == 200:
            data = res.json()
            bot_response = data.get("response", "Processing complete.")
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": bot_response
            })
        else:
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": f"❌ **Backend Error ({res.status_code}):** {res.text}"
            })
    except Exception as e:
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": f"❌ **Connection Error:** Could not connect to server. ({e})"
        })
    
    st.session_state.user_input_text = ""

# Header & Sidebar Auth
st.markdown("""
    <div class="bsnl-header">
        <div class="bsnl-title">📶 BSNL Trouble Ticket Solving Agent</div>
        <div class="bsnl-subtitle">Automated CRM Triage, Technical Fault Diagnostics & Ticket Dispatch Portal</div>
    </div>
""", unsafe_allow_html=True)

st.sidebar.markdown("### 🔒 **OFFICER AUTHENTICATION**")

if not st.session_state.access_token:
    with st.sidebar.form("login_form"):
        username_input = st.text_input("Username", value="emp101")
        password_input = st.text_input("Password", type="password", value="password123")
        if st.form_submit_button("LOGIN"):
            try:
                response = requests.post(
                    f"{API_BASE_URL}/login",
                    data={"username": username_input, "password": password_input},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=10
                )
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.access_token = data.get("access_token")
                    st.session_state.username = username_input
                    st.session_state.session_id = data.get("session_id")
                    st.session_state.default_thread_id = data.get("default_thread_id")
                    st.rerun()
                else:
                    st.sidebar.error("Authentication Failed.")
            except Exception as e:
                st.sidebar.error(f"Backend Server Unreachable: {e}")
else:
    st.sidebar.success(f"LOGGED IN AS: {st.session_state.username.upper()}")
    if st.sidebar.button("CLEAR CHAT HISTORY"):
        st.session_state.chat_history = []
        st.rerun()
    if st.sidebar.button("LOGOUT"):
        st.session_state.access_token = None
        st.session_state.chat_history = []
        st.rerun()

# Main Interface
if not st.session_state.access_token:
    st.info("🔒 **Access Restricted:** Please enter BSNL officer credentials in the sidebar to open the workspace.")
else:
    tab1, tab2 = st.tabs(["💬 **Issue Resolution Terminal**", "🔍 **Ticket Status Lookup**"])

    with tab1:
        st.markdown("### **BSNL Support Terminal**")
        
        # Permanent Top Input Bar
        st.text_input(
            "Enter issue description or request ticket creation:",
            key="user_input_text",
            placeholder="Type your issue and press Enter...",
            on_change=handle_submit
        )

        st.markdown("---")
        
        # Chat History
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    with tab2:
        st.markdown("### **Query Active Trouble Ticket**")
        ticket_input = st.text_input("HubSpot Ticket ID", placeholder="Enter ticket ID (e.g. 3847291048)")
        
        if st.button("SEARCH TICKET STATUS", type="primary"):
            if ticket_input.strip():
                headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
                with st.spinner("Fetching record from HubSpot..."):
                    try:
                        res = requests.get(
                            f"{API_BASE_URL}/triage/status/{ticket_input.strip()}", 
                            headers=headers,
                            timeout=15
                        )
                        if res.status_code == 200:
                            st.success("Ticket Record Found")
                            st.json(res.json())
                        else:
                            st.error(f"Error {res.status_code}: {res.text}")
                    except Exception as e:
                        st.error(f"Failed to query endpoint: {e}")
