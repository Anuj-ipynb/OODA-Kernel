import time
from datetime import datetime, timezone
from app.core.state import IncidentState

def observe_node(state: IncidentState) -> dict:
    """
    Observe Node: Normalizes raw incident telemetry and log dumps.
    """
    start_time = time.time()
    telemetry = state.get("telemetry_logs", "")
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Process and summarize raw logs
    normalized_summary = f"Processed telemetry log trace ({len(telemetry)} chars)"
    latency_ms = round((time.time() - start_time) * 1000, 2)
    
    step_item = {
        "node": "observe",
        "status": "COMPLETED",
        "timestamp": timestamp,
        "latency_ms": latency_ms,
        "details": {"summary": normalized_summary}
    }
    
    return {
        "status": "OBSERVING",
        "step_history": [step_item]
    }
