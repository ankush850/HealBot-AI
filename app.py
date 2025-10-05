
import streamlit as st
import requests
import json
import time
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Any
import uuid


# --- Page Configuration ---
st.set_page_config(
    page_title="HealBot AI - Smart Health & Emergency Dashboard",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling (from dashboard)
st.markdown("""
<style>
    .alert-critical {
        background-color: #f8d7da;
        border: 2px solid #dc3545;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        animation: pulse 2s infinite;
    }
    .alert-high {
        background-color: #fff3cd;
        border: 2px solid #ffc107;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
    }
    .alert-moderate {
        background-color: #d4edda;
        border: 2px solid #28a745;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
    }
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(220, 53, 69, 0.7); }
        70% { box-shadow: 0 0 0 10px rgba(220, 53, 69, 0); }
        100% { box-shadow: 0 0 0 0 rgba(220, 53, 69, 0); }
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .status-connected {
        color: #28a745;
    }
    .status-error {
        color: #dc3545;
    }
</style>
""", unsafe_allow_html=True)


# --- EmergencyDashboard class from user code ---
API_BASE_URL = "http://127.0.0.1:8000"
REFRESH_INTERVAL = 10  # seconds

class EmergencyDashboard:
    def __init__(self):
        self.api_connected = False
        self.last_check = None
    def check_api_connection(self) -> bool:
        try:
            # Use the lightweight /status endpoint (quick)
            response = requests.get(f"{API_BASE_URL}/status", timeout=5)
            if response.status_code == 200:
                self.api_connected = True
                return True
        except Exception as e:
            st.error(f"API Connection Error: {e}")
        self.api_connected = False
        return False
    def get_current_alerts(self) -> List[Dict[str, Any]]:
        try:
            response = requests.get(f"{API_BASE_URL}/alerts/current", timeout=15)
            if response.status_code == 200:
                data = response.json()
                return data.get('alerts', [])
            else:
                st.error(f"API Error: {response.status_code}")
                return []
        except Exception as e:
            st.error(f"Error fetching alerts: {e}")
            return []
    def get_simulation_status(self) -> Dict[str, Any]:
        try:
            response = requests.get(f"{API_BASE_URL}/simulation/status", timeout=10)
            if response.status_code == 200:
                return response.json()
            return {"available": False, "error": "API unavailable"}
        except Exception as e:
            return {"available": False, "error": str(e)}
    def run_simulation(self, simulation_type: str) -> Dict[str, Any]:
        try:
            response = requests.post(f"{API_BASE_URL}/simulation/run/{simulation_type}", timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    def reset_simulation_data(self) -> bool:
        try:
            response = requests.post(f"{API_BASE_URL}/simulation/reset", timeout=10)
            return response.status_code == 200
        except Exception as e:
            st.error(f"Error resetting data: {e}")
            return False
    def process_emergency_report(self, query: str) -> Dict[str, Any]:
        try:
            data = {
                "query": query,
                "session_id": f"streamlit-{int(time.time())}"
            }
            response = requests.post(f"{API_BASE_URL}/emergency/process", json=data, timeout=20)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    def display_alert(self, alert: Dict[str, Any]):
        # Defensive: handle if alert is a string or dict
        if isinstance(alert, str):
            st.warning(f"Alert: {alert}")
            return
        raw_alert = alert.get('raw_data', alert)
        if isinstance(raw_alert, str):
            try:
                raw_alert = json.loads(raw_alert)
            except Exception:
                st.warning(f"Alert: {raw_alert}")
                return
        alert_level = raw_alert.get('alert_level', 'UNKNOWN').lower()
        css_class = f"alert-{alert_level}" if alert_level in ['critical', 'high', 'moderate'] else "alert-moderate"
        title = raw_alert.get('title', 'Emergency Alert')
        summary = raw_alert.get('summary', 'Alert details unavailable')
        alert_type = raw_alert.get('alert_type', 'unknown')
        timestamp = raw_alert.get('timestamp', datetime.now().isoformat())
        try:
            alert_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            time_str = alert_time.strftime('%Y-%m-%d %H:%M:%S')
        except:
            time_str = timestamp
        alert_html = f"""
        <div class="{css_class}">
            <h3>🚨 {title}</h3>
            <p><strong>Level:</strong> {alert_level.upper()}</p>
            <p><strong>Type:</strong> {alert_type.replace('_', ' ').title()}</p>
            <p><strong>Summary:</strong> {summary}</p>
            <p><strong>Time:</strong> {time_str}</p>
        </div>
        """
        st.markdown(alert_html, unsafe_allow_html=True)
        details = raw_alert.get('details', {})
        if details:
            with st.expander("View Detailed Information"):
                st.json(details)
        recommendations = raw_alert.get('recommendations', [])
        immediate_actions = raw_alert.get('immediate_actions', [])
        if recommendations:
            st.write("**Recommendations:**")
            for rec in recommendations:
                st.write(f"• {rec}")
        if immediate_actions:
            st.write("**Immediate Actions:**")
            for action in immediate_actions:
                st.write(f"• {action}")
        contacts = raw_alert.get('emergency_contacts', {})
        if contacts:
            st.write("**Emergency Contacts:**")
            for service, number in contacts.items():
                st.write(f"• {service.replace('_', ' ').title()}: {number}")


# --- Main App Tabs ---
tabs = st.tabs(["💬 Health Agent Chat", "🚨 Emergency Dashboard"])

# --- Tab 1: Health Agent Chat (original chat UI) ---
with tabs[0]:
    st.title("🤖 HealBot AI")
    st.caption(f"Your Smart Health & Emergency Assistant | Operating for Warangal, Telangana | {datetime.now().strftime('%B %d, %Y')}")

    # --- Check and Display Emergency Status Banner ---
    try:
        status_response = requests.get(f"{API_BASE_URL}/status")
        if status_response.status_code == 200 and status_response.json().get("emergency_mode_active"):
            st.error(
                " **EMERGENCY MODE ACTIVE** | The system is currently operating in emergency response mode. Please describe your situation or symptoms for immediate classification.",
            )
            default_message = "EMERGENCY ACTIVE: Please describe your situation or symptoms."
        else:
            default_message = "Hello! How can I help you with your health today?"
    except requests.exceptions.ConnectionError:
        st.warning("Could not connect to the backend server.")
        default_message = "Connection to the server failed. Please ensure the backend is running."

    # --- Session State Initialization ---
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": default_message}]

    # --- Display Chat History ---
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # --- Handle User Input ---
    if prompt := st.chat_input("Ask about health or describe your symptoms..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("Thinking...")
            try:
                api_url = f"{API_BASE_URL}/chat"
                payload = {
                    "query": prompt,
                    "session_id": st.session_state.session_id
                }
                response = requests.post(api_url, json=payload)
                response.raise_for_status()
                agent_response = response.json()["response"]
                message_placeholder.markdown(agent_response)
                st.session_state.messages.append({"role": "assistant", "content": agent_response})
            except requests.exceptions.RequestException as e:
                error_message = f"Could not connect to the AI backend. Please make sure the FastAPI server is running. Error: {e}"
                message_placeholder.markdown(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})

# --- Tab 2: Emergency Dashboard (user's dashboard UI) ---
with tabs[1]:
    dashboard = EmergencyDashboard()
    st.title("🚨 Emergency Alert System - Warangal District")
    st.markdown("Real-time Emergency Monitoring & Response System")

    st.sidebar.header("Control Panel")
    api_status = dashboard.check_api_connection()
    if api_status:
        st.sidebar.markdown('<p class="status-connected">🟢 API Connected</p>', unsafe_allow_html=True)
    else:
        st.sidebar.markdown('<p class="status-error">🔴 API Disconnected</p>', unsafe_allow_html=True)
    auto_refresh = st.sidebar.checkbox("Auto-refresh alerts", value=True)
    refresh_rate = st.sidebar.slider("Refresh interval (seconds)", 5, 60, REFRESH_INTERVAL)
    if st.sidebar.button("🔄 Refresh Now"):
        st.rerun()
    st.sidebar.subheader("Simulation Controls")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("🦠 Simulate Outbreak"):
            with st.spinner("Running outbreak simulation..."):
                result = dashboard.run_simulation("outbreak")
                if 'error' not in result:
                    st.success(f"Simulation completed: {result.get('reports_processed', 0)} reports")
                    if result.get('alerts_generated', 0) > 0:
                        st.success("🚨 Alert generated!")
                else:
                    st.error(f"Simulation failed: {result['error']}")
    with col2:
        if st.button("🌊 Simulate Disaster"):
            with st.spinner("Running disaster simulation..."):
                result = dashboard.run_simulation("disaster")
                if 'error' not in result:
                    st.success(f"Simulation completed: {result.get('reports_processed', 0)} reports")
                    if result.get('alerts_generated', 0) > 0:
                        st.success("🚨 Alert generated!")
                else:
                    st.error(f"Simulation failed: {result['error']}")
    if st.sidebar.button("🗑️ Reset All Data"):
        if dashboard.reset_simulation_data():
            st.success("All simulation data reset successfully")
        else:
            st.error("Failed to reset simulation data")

    if not api_status:
        st.error("Cannot connect to the emergency system API. Please ensure the API is running on localhost:8000")
        st.code("python main.py", language="bash")
    else:
        tab1, tab2, tab3, tab4 = st.tabs(["🚨 Active Alerts", "📊 System Status", "📝 Report Emergency", "📈 Analytics"])
        with tab1:
            st.header("Active Emergency Alerts")
            alerts = dashboard.get_current_alerts()
            if alerts:
                st.warning(f"⚠️ {len(alerts)} active emergency alert(s)")
                for i, alert in enumerate(alerts):
                    st.subheader(f"Alert {i+1}")
                    dashboard.display_alert(alert)
                    st.divider()
            else:
                st.success("✅ No active alerts at this time")
                st.info("The system is continuously monitoring for emergency situations...")
        with tab2:
            st.header("System Status")
            status = dashboard.get_simulation_status()
            if status.get('available'):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Reports", status.get('total_emergency_reports', 0))
                with col2:
                    st.metric("Outbreak Reports", status.get('total_epidemic_reports', 0))
                with col3:
                    st.metric("Active Alerts", status.get('current_alerts', 0))
                with col4:
                    st.metric("System Status", "Online" if api_status else "Offline")
                st.subheader("System Health")
                st.success("Emergency monitoring system operational")
                st.info(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                st.error(f"System Status Error: {status.get('error', 'Unknown error')}")
        with tab3:
            st.header("Report Emergency")
            with st.form("emergency_report_form"):
                st.write("Use this form to report an emergency situation:")
                emergency_type = st.selectbox(
                    "Emergency Type",
                    ["Disease Outbreak", "Natural Disaster", "Medical Emergency"]
                )
                description = st.text_area(
                    "Description",
                    placeholder="Describe the emergency situation, symptoms, or conditions...",
                    height=100
                )
                location = st.text_input("Location", value="Warangal, Telangana", disabled=True)
                submitted = st.form_submit_button("🚨 Submit Emergency Report")
                if submitted and description:
                    with st.spinner("Processing emergency report..."):
                        result = dashboard.process_emergency_report(description)
                        if 'error' not in result:
                            st.success("Emergency report submitted successfully!")
                            st.subheader("Emergency Response")
                            st.write(result.get('emergency_response', 'Report processed'))
                            if result.get('public_alert_generated'):
                                st.warning("🚨 This report triggered a public alert!")
                                st.json(result['public_alert_generated'])
                        else:
                            st.error(f"Error processing report: {result['error']}")
                elif submitted:
                    st.error("Please provide a description of the emergency")
        with tab4:
            st.header("Analytics Dashboard")
            st.info("Analytics dashboard coming soon...")
            st.write("This section will include:")
            st.write("• Alert frequency trends")
            st.write("• Geographic distribution of reports")
            st.write("• Response time metrics")
            st.write("• System performance indicators")
        if auto_refresh and api_status:
            time.sleep(refresh_rate)
            st.rerun()
# [2025-10-01] feat(booking): implement doctor appointment booking workflow

# [2025-10-05] refactor(agent): streamline LLM output parsing with Pydantic schemas
