import streamlit as st
import requests
import json
import time

API_BASE_URL = "http://localhost:8000/api/incident"

st.set_page_config(
    page_title="OODA-Kernel | HITL Control Dashboard",
    page_icon="🛡️",
    layout="wide"
)

# Custom CSS styling
st.markdown("""
<style>
    .main { background-color: #0E1117; }
    .stApp { color: #FAFAFA; }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    .metric-card {
        background-color: #1E232A;
        border: 1px solid #30363D;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ OODA-Kernel: Autonomous Remediation Dashboard")
st.caption("Stateful AI Incident Recovery Engine with Human-in-the-Loop Guardrails")

# Sidebar: Environment & Server Info
with st.sidebar:
    st.header("⚙️ System Status")
    try:
        res = requests.get("http://localhost:8000/health", timeout=2)
        if res.status_code == 200:
            st.success("API Server: Connected")
        else:
            st.error("API Server: Error")
    except Exception:
        st.warning("API Server: Not running (Start uvicorn)")
        
    st.divider()
    st.subheader("Threshold Policy")
    st.info("High-Risk Threshold: `risk_score > 0.70`\nRequires Operator Approval")

# Main Interface Tabs
tab1, tab2 = st.tabs(["🚀 Ingest Telemetry", "📋 Incident Monitor & Approvals"])

with tab1:
    st.subheader("Submit Raw Telemetry")
    telemetry_input = st.text_area(
        "Paste log dump, alert message, or Prometheus metric output:",
        value="2026-08-16 11:00:00 [ERROR] Connection pool exhausted: postgresql://db:5432",
        height=120
    )
    
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("Trigger OODA Pipeline", type="primary"):
            with st.spinner("Processing OODA Graph..."):
                try:
                    payload = {"telemetry": telemetry_input, "max_retries": 3}
                    response = requests.post(f"{API_BASE_URL}/submit", json=payload)
                    if response.status_code == 200:
                        data = response.json()
                        st.session_state["last_incident_id"] = data["incident_id"]
                        st.success(f"Incident Submitted! ID: `{data['incident_id']}`")
                        st.json(data)
                    else:
                        st.error(f"API Error: {response.text}")
                except Exception as e:
                    st.error(f"Failed to connect to backend: {e}")

with tab2:
    st.subheader("Incident Details & Approval Controls")
    incident_id = st.text_input(
        "Enter Incident ID:",
        value=st.session_state.get("last_incident_id", "")
    )
    
    if incident_id:
        try:
            res = requests.get(f"{API_BASE_URL}/{incident_id}/state")
            if res.status_code == 200:
                state_data = res.json()
                values = state_data.get("values", {})
                
                # Metrics Row
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Status", values.get("status", "UNKNOWN"))
                m2.metric("Risk Score", f"{values.get('risk_score', 0.0):.2f}")
                m3.metric("Destructive?", "YES" if values.get("is_destructive") else "NO")
                m4.metric("Verified?", "YES" if values.get("is_verified") else "NO")
                
                st.divider()
                
                # HITL Approval Card if Interrupted
                if values.get("status") == "AWAITING_APPROVAL" or (values.get("risk_score", 0) > 0.70 and not values.get("is_verified")):
                    st.warning("⚠️ **APPROVAL REQUIRED**: Proposed action exceeds risk safety threshold!")
                    st.markdown(f"**Proposed Command**: `{values.get('proposed_command')}`")
                    st.markdown(f"**Root Cause**: {values.get('root_cause_analysis')}")
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅ Approve & Resume Execution", type="primary"):
                            approve_res = requests.post(
                                f"{API_BASE_URL}/{incident_id}/approve",
                                json={"approved": True, "operator_notes": "Approved via Streamlit UI"}
                            )
                            if approve_res.status_code == 200:
                                st.success("Execution approved and completed!")
                                st.rerun()
                            else:
                                st.error(approve_res.text)
                    with c2:
                        if st.button("❌ Reject Action"):
                            approve_res = requests.post(
                                f"{API_BASE_URL}/{incident_id}/approve",
                                json={"approved": False, "operator_notes": "Rejected by operator"}
                            )
                            st.error("Execution rejected.")
                            st.rerun()
                            
                # Timeline History
                st.subheader("📜 OODA Step History Log")
                history = values.get("step_history", [])
                st.dataframe(history, use_container_width=True)
                
            else:
                st.error("Incident ID not found.")
        except Exception as e:
            st.error(f"Error fetching state: {e}")
