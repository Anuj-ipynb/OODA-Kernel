from datetime import datetime, timezone
from app.core.state import IncidentState

def observe_node(state: IncidentState) -> dict:
    """
    Observe Node: Normalizes raw incident telemetry and log dumps.
    """
    telemetry = state.get("telemetry_logs", "")
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Process and summarize raw logs
    normalized_summary = f"Processed telemetry log trace ({len(telemetry)} chars)"
    
    step_item = {
        "node": "observe",
        "status": "completed",
        "timestamp": timestamp,
        "details": {"summary": normalized_summary}
    }
    
    return {
        "status": "OBSERVING",
        "step_history": [step_item]
    }
