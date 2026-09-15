import json

import requests
import streamlit as st

API_BASE_URL = "http://localhost:8000/api/incident"

st.set_page_config(
    page_title="OODA-Kernel | Autonomous Remediation Control Plane",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Glassmorphism & High-Contrast CSS Styling
st.markdown("""
<style>
    .main { background-color: #0B0E14; }
    .stApp { color: #E6EDF3; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
    
    .stButton>button {
        border-radius: 6px;
        font-weight: 600;
        transition: all 0.2s ease-in-out;
    }
    
    /* Card Container */
    .glass-card {
        background: rgba(22, 27, 34, 0.85);
        border: 1px solid #30363D;
        border-radius: 10px;
        padding: 18px;
        margin-bottom: 16px;
        backdrop-filter: blur(10px);
    }
    
    /* Node Status Badges */
    .badge-pending { background-color: #484F58; color: #F0F6FC; padding: 3px 10px; border-radius: 12px; font-weight: 600; font-size: 0.85rem; }
    .badge-running { background-color: #1F6FEB; color: #FFFFFF; padding: 3px 10px; border-radius: 12px; font-weight: 600; font-size: 0.85rem; animation: pulse 1.5s infinite; }
    .badge-hitl { background-color: #D29922; color: #0D1117; padding: 3px 10px; border-radius: 12px; font-weight: 700; font-size: 0.85rem; }
    .badge-resolved { background-color: #238636; color: #FFFFFF; padding: 3px 10px; border-radius: 12px; font-weight: 600; font-size: 0.85rem; }
    .badge-failed { background-color: #DA3633; color: #FFFFFF; padding: 3px 10px; border-radius: 12px; font-weight: 600; font-size: 0.85rem; }
    
    @keyframes pulse {
        0% { opacity: 0.6; }
        50% { opacity: 1.0; }
        100% { opacity: 0.6; }
    }

    /* Side-by-Side Diff Header */
    .diff-before {
        background-color: rgba(218, 54, 51, 0.15);
        border: 1px solid #782A29;
        border-radius: 8px;
        padding: 14px;
    }
    .diff-after {
        background-color: rgba(35, 134, 54, 0.15);
        border: 1px solid #1B4B27;
        border-radius: 8px;
        padding: 14px;
    }
    
    /* Countdown Banner */
    .countdown-banner {
        background: linear-gradient(90deg, #782A29 0%, #D29922 100%);
        color: #FFFFFF;
        border-radius: 8px;
        padding: 12px;
        font-weight: 700;
        text-align: center;
        margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ OODA-Kernel: Incident Control Plane")
st.caption("Autonomous Self-Healing Engine with Interactive DAG Visualizer & Side-by-Side Diff HITL Approvals")

# --- Session State Initialization ---
if "execution_mode" not in st.session_state:
    st.session_state["execution_mode"] = "mock"
if "last_incident_id" not in st.session_state:
    st.session_state["last_incident_id"] = ""
if "operator_id" not in st.session_state:
    st.session_state["operator_id"] = "OP-SYS-9021"

# --- Sidebar Controls & System Status ---
with st.sidebar:
    st.header("⚙️ Control Settings")
    
    # Target Execution Backend Selector
    mode_selection = st.radio(
        "🎯 Target Execution Environment:",
        options=["Mock Sandbox", "Staging Cluster", "Production Cluster"],
        index=0,
        help="Production environment forces HITL approval regardless of risk score."
    )
    
    mode_map = {"Mock Sandbox": "mock", "Staging Cluster": "staging", "Production Cluster": "production"}
    st.session_state["execution_mode"] = mode_map[mode_selection]
    
    st.divider()
    st.subheader("👤 Operator Identity")
    st.session_state["operator_id"] = st.text_input("Operator ID / Badge:", value=st.session_state["operator_id"])
    
    st.divider()
    st.subheader("🌐 System Connectivity")
    try:
        res = requests.get("http://localhost:8000/health", timeout=2)
        if res.status_code == 200:
            data = res.json()
            st.success(f"FastAPI Backend: Connected (v{data.get('version', '0.3.0')})")
        else:
            st.error("FastAPI Backend: HTTP Error")
    except Exception:  # noqa: BLE001
        st.warning("FastAPI Backend: Offline (Start uvicorn)")

    st.info("💡 Safety Policy: `risk_score > 0.70` or `is_destructive == True` triggers automatic HITL approval barrier.")

# --- Main Navigation Tabs ---
tab1, tab2, tab3 = st.tabs([
    "🚀 Live Ingest & Webhooks",
    "📊 DAG Visualizer & HITL Approvals",
    "📜 Immutable Audit Trail & Logs"
])

# ==============================================================================
# TAB 1: Live Ingest & Webhook Streams
# ==============================================================================
with tab1:
    st.subheader("📥 Ingest Telemetry Stream")
    
    ingest_type = st.selectbox(
        "Select Telemetry Source Formatter:",
        options=["Raw Log Dump", "Prometheus Alertmanager", "PagerDuty Incident V2", "OpenTelemetry Trace/Log"]
    )
    
    default_payloads = {
        "Raw Log Dump": "2026-08-17 07:00:00 [CRITICAL] postgresql://db:5432 - Connection pool exhausted (500/500 connections active). Max pool size exceeded.",
        "Prometheus Alertmanager": json.dumps({
            "alerts": [
                {
                    "status": "firing",
                    "labels": {"alertname": "PostgresConnectionPoolExhausted", "severity": "critical"},
                    "annotations": {"summary": "PostgreSQL connection pool exhausted on db-primary:5432"}
                }
            ]
        }, indent=2),
        "PagerDuty Incident V2": json.dumps({
            "messages": [
                {
                    "event": "incident.trigger",
                    "incident": {
                        "title": "High Memory Pressure & OOM Kills on API Gateway Pods",
                        "service": {"summary": "api-gateway-k8s"}
                    }
                }
            ]
        }, indent=2),
        "OpenTelemetry Trace/Log": json.dumps({
            "resourceLogs": [
                {
                    "scopeLogs": [
                        {
                            "logRecords": [
                                {"body": {"stringValue": "[FATAL] Host disk space exhausted (/var/log/app.log 99% full)"}}
                            ]
                        }
                    ]
                }
            ]
        }, indent=2)
    }
    
    telemetry_input = st.text_area(
        "Payload Content:",
        value=default_payloads.get(ingest_type, ""),
        height=150
    )
    
    c1, c2 = st.columns([1, 3])
    with c1:
        if st.button("⚡ Dispatch to OODA Kernel", type="primary", use_container_width=True):
            with st.spinner("Executing OODA Graph Pipeline..."):
                try:
                    mode = st.session_state["execution_mode"]
                    if ingest_type == "Raw Log Dump":
                        endpoint = f"{API_BASE_URL}/submit"
                        payload = {"telemetry": telemetry_input, "execution_mode": mode, "max_retries": 3}
                    elif ingest_type == "Prometheus Alertmanager":
                        endpoint = f"{API_BASE_URL}/webhook/alertmanager?mode={mode}"
                        payload = json.loads(telemetry_input)
                    elif ingest_type == "PagerDuty Incident V2":
                        endpoint = f"{API_BASE_URL}/webhook/pagerduty?mode={mode}"
                        payload = json.loads(telemetry_input)
                    else:
                        endpoint = f"{API_BASE_URL}/webhook/otel?mode={mode}"
                        payload = json.loads(telemetry_input)
                        
                    res = requests.post(endpoint, json=payload, timeout=120)
                    if res.status_code == 200:
                        data = res.json()
                        st.session_state["last_incident_id"] = data.get("incident_id", "")
                        st.success(f"Incident Submitted! ID: `{data.get('incident_id')}` | Status: `{data.get('status')}`")
                        st.json(data)
                    else:
                        st.error(f"API Error ({res.status_code}): {res.text}")
                except Exception as e:  # noqa: BLE001
                    st.error(f"Execution Error: {e}")

# ==============================================================================
# TAB 2: Interactive DAG Visualizer & Side-by-Side Diff HITL Approvals
# ==============================================================================
with tab2:
    col_input, col_refresh = st.columns([4, 1])
    with col_input:
        incident_id = st.text_input(
            "Incident ID:",
            value=st.session_state.get("last_incident_id", ""),
            placeholder="Enter Incident UUID..."
        )
    with col_refresh:
        st.write("")
        st.write("")
        refresh_btn = st.button("🔄 Refresh State", use_container_width=True)

    if incident_id:
        try:
            res = requests.get(f"{API_BASE_URL}/{incident_id}/state", timeout=5)
            if res.status_code == 200:
                state_data = res.json()
                values = state_data.get("values", {})
                
                status = values.get("status", "UNKNOWN")
                risk_score = values.get("risk_score", 0.0)
                is_destructive = values.get("is_destructive", False)
                is_verified = values.get("is_verified", False)
                mode = values.get("execution_mode", "mock")
                step_history = values.get("step_history", [])
                
                # --- Metrics Header Bar ---
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Incident Status", status)
                m2.metric("Execution Target", mode.upper())
                m3.metric("Risk Score", f"{risk_score:.2f}")
                m4.metric("Destructive Action?", "YES ⚠️" if is_destructive else "NO ✅")
                m5.metric("Post-Verification", "VERIFIED ✅" if is_verified else "PENDING ⏳")
                
                st.divider()

                # ----------------------------------------------------------------------
                # REQUIREMENT 2: Side-by-Side Diff & Approval Card (If Interrupted)
                # ----------------------------------------------------------------------
                if status == "AWAITING_APPROVAL" or (risk_score > 0.70 and not is_verified):
                    st.markdown("""
                    <div class="countdown-banner">
                        ⚠️ HIGH-RISK ACTION INTERRUPTED: Operator Sign-off Required
                    </div>
                    """, unsafe_allow_html=True)

                    # 60-second Countdown Timer Scaffolding
                    countdown_placeholder = st.empty()
                    countdown_placeholder.info("⏱️ **Safety Timeout Active**: Auto-abort in 60s if unconfirmed.")

                    # Blast Radius & Action Summary Alert Card
                    st.error(f"🚨 **Blast Radius Warning**: Proposed remediation commands will affect target environment (`{mode.upper()}`).")
                    
                    # Split-Screen Diff Pane (Before vs. Proposed After)
                    d_col1, d_col2 = st.columns(2)
                    with d_col1:
                        st.markdown("""
                        <div class="diff-before">
                            <h4>🔴 Current System State (Before)</h4>
                            <hr style="margin: 8px 0; border-color: #782A29;"/>
                        """, unsafe_allow_html=True)
                        rca = values.get("root_cause_analysis", {})
                        if isinstance(rca, dict):
                            st.write(f"**Root Cause**: {rca.get('root_cause', 'Unknown')}")
                            st.write(f"**Impacted Services**: {', '.join(rca.get('impacted_services', []))}")
                            st.write(f"**Confidence**: {rca.get('confidence_score', 0.9):.2f}")
                        else:
                            st.write(f"**Diagnosis**: {rca}")
                        st.code(values.get("telemetry_logs", "No logs")[:300], language="text")
                        st.markdown("</div>", unsafe_allow_html=True)
                        
                    with d_col2:
                        st.markdown("""
                        <div class="diff-after">
                            <h4>🟢 Proposed Remediation & Rollback (After)</h4>
                            <hr style="margin: 8px 0; border-color: #1B4B27;"/>
                        """, unsafe_allow_html=True)
                        st.markdown(f"**Proposed Command**: `{values.get('proposed_command')}`")
                        st.markdown(f"**Rollback Command**: `{values.get('rollback_command')}`")
                        st.markdown(f"**Risk Level**: `{risk_score:.2f}` / 1.00")
                        st.markdown("</div>", unsafe_allow_html=True)
                    
                    st.write("")
                    
                    # Inline Approval Form Controls
                    ap_c1, ap_c2, ap_c3 = st.columns([2, 2, 2])
                    with ap_c1:
                        op_id = st.text_input("Operator Badge ID:", value=st.session_state["operator_id"], key="op_badge")
                    with ap_c2:
                        op_notes = st.text_input("Operator Audit Notes:", value="Verified state diff & blast radius.", key="op_notes")
                    
                    b_col1, b_col2 = st.columns(2)
                    with b_col1:
                        if st.button("✅ [Approve & Run]", type="primary", use_container_width=True):
                            with st.spinner("Authorizing & resuming graph..."):
                                approve_payload = {
                                    "approved": True,
                                    "operator_id": op_id,
                                    "operator_notes": op_notes
                                }
                                approve_res = requests.post(f"{API_BASE_URL}/{incident_id}/approve", json=approve_payload)
                                if approve_res.status_code == 200:
                                    st.success("Remediation Approved & Executed!")
                                    st.rerun()
                                else:
                                    st.error(f"Approval Error: {approve_res.text}")
                    with b_col2:
                        if st.button("❌ [Reject & Abort]", use_container_width=True):
                            with st.spinner("Aborting execution..."):
                                approve_payload = {
                                    "approved": False,
                                    "operator_id": op_id,
                                    "operator_notes": op_notes
                                }
                                approve_res = requests.post(f"{API_BASE_URL}/{incident_id}/approve", json=approve_payload)
                                st.warning("Execution Rejected & Aborted by Operator.")
                                st.rerun()

                    st.divider()

                # ----------------------------------------------------------------------
                # REQUIREMENT 1: Interactive Graph Visualizer & Timeline Cards
                # ----------------------------------------------------------------------
                st.subheader("🕸️ Stateful OODA Directed Acyclic Graph (DAG)")
                
                # Derive node statuses from step history
                node_history_map = {step.get("node"): step for step in step_history if isinstance(step, dict)}
                
                nodes = ["observe", "orient", "decide", "hitl_gateway", "act", "verify", "rollback"]
                
                def get_node_color_and_status(node_name: str) -> tuple[str, str, float]:
                    if node_name in node_history_map:
                        item = node_history_map[node_name]
                        st_val = item.get("status", "COMPLETED").upper()
                        lat = item.get("latency_ms", 0.0)
                        if st_val in ["COMPLETED", "RESOLVED"]:
                            return "#238636", "RESOLVED", lat
                        elif st_val in ["FAILED", "REJECTED"]:
                            return "#DA3633", "FAILED", lat
                        elif st_val == "PAUSED_HITL":
                            return "#D29922", "PAUSED_HITL", lat
                        else:
                            return "#1F6FEB", "RUNNING", lat
                    elif status == "AWAITING_APPROVAL" and node_name == "hitl_gateway":
                        return "#D29922", "PAUSED_HITL", 0.0
                    else:
                        return "#30363D", "PENDING", 0.0

                # Render Graphviz Interactive Diagram
                dot_lines = ["digraph OODA {", "rankdir=LR;", "node [shape=rectangle, style=filled, fontname=\"Helvetica\", fontcolor=white];"]
                for n in nodes:
                    color, st_label, lat = get_node_color_and_status(n)
                    label_str = f"{n.upper()}\\n[{st_label}]"
                    if lat > 0:
                        label_str += f"\\n{lat}ms"
                    dot_lines.append(f'  "{n}" [label="{label_str}", fillcolor="{color}"];')
                
                dot_lines.extend([
                    '  "observe" -> "orient";',
                    '  "orient" -> "decide";',
                    '  "decide" -> "hitl_gateway";',
                    '  "hitl_gateway" -> "act" [label="Approve"];',
                    '  "act" -> "verify";',
                    '  "verify" -> "rollback" [label="Verify Failed"];',
                    '  "rollback" -> "orient" [label="Retry"];'
                ])
                dot_lines.append("}")
                
                st.graphviz_chart("\n".join(dot_lines), use_container_width=True)

                # Render Node Timeline Cards with Inline Latency & Confidence
                st.subheader("📋 Step Timeline & Performance Metrics")
                t_cols = st.columns(len(nodes))
                for idx, n in enumerate(nodes):
                    color, st_label, lat = get_node_color_and_status(n)
                    with t_cols[idx]:
                        badge_class = "badge-pending"
                        if st_label == "RESOLVED": badge_class = "badge-resolved"
                        elif st_label == "FAILED": badge_class = "badge-failed"
                        elif st_label == "PAUSED_HITL": badge_class = "badge-hitl"
                        elif st_label == "RUNNING": badge_class = "badge-running"
                        
                        st.markdown(f"""
                        <div class="glass-card" style="text-align: center; padding: 10px;">
                            <span class="{badge_class}">{st_label}</span>
                            <h5 style="margin-top: 8px; margin-bottom: 4px;">{n.upper()}</h5>
                            <p style="font-size: 0.8rem; color: #8B949E; margin: 0;">Latency: <b>{lat:.1f}ms</b></p>
                        </div>
                        """, unsafe_allow_html=True)
                        
            else:
                st.error("Incident ID not found.")
        except Exception as e:  # noqa: BLE001
            st.error(f"Error fetching state: {e}")

# ==============================================================================
# TAB 3: Immutable Audit Trail & Logs
# ==============================================================================
with tab3:
    st.subheader("📜 Immutable Audit Log & State Tracing")
    
    audit_incident_id = st.text_input(
        "Audit Search Incident ID:",
        value=st.session_state.get("last_incident_id", ""),
        key="audit_search_input"
    )
    
    if audit_incident_id:
        try:
            res = requests.get(f"{API_BASE_URL}/{audit_incident_id}/state", timeout=5)
            if res.status_code == 200:
                state_data = res.json()
                values = state_data.get("values", {})
                audit_trail = values.get("audit_trail", [])
                
                st.markdown("#### 🔒 Immutable Security Audit Log")
                if audit_trail:
                    st.dataframe(audit_trail, use_container_width=True)
                else:
                    st.info("No audit security events recorded for this incident yet.")
                    
                st.divider()
                st.markdown("#### 🔍 Full OODA State Snapshot Trace")
                st.json(values)
            else:
                st.error("Incident ID state not found.")
        except Exception as e:  # noqa: BLE001
            st.error(f"Error loading audit trail: {e}")
