from datetime import datetime, timezone
from app.core.state import IncidentState

def rollback_node(state: IncidentState) -> dict:
    """
    Rollback Node: Increments retry counter and prepares state snapshot for re-orientation.
    """
    current_retries = state.get("retry_count", 0)
    timestamp = datetime.now(timezone.utc).isoformat()
    new_retries = current_retries + 1
    
    error_msg = f"[ROLLBACK] Remediation failed verification (Attempt {new_retries}/{state.get('max_retries', 3)}). Rolling back state to re-orient."
    
    step_item = {
        "node": "rollback",
        "status": "completed",
        "timestamp": timestamp,
        "details": {"retry_count": new_retries, "reason": error_msg}
    }
    
    return {
        "status": "ROLLING_BACK",
        "retry_count": new_retries,
        "is_verified": False,
        "error_log": [error_msg],
        "step_history": [step_item]
    }
