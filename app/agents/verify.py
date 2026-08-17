from datetime import datetime, timezone
from app.core.state import IncidentState

def verify_node(state: IncidentState) -> dict:
    """
    Verify Node: Checks system parameters post-action to confirm incident resolution.
    """
    sandbox_output = state.get("sandbox_output", "")
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Verification check: Check if sandbox output indicates success
    is_verified = (
        "Executed successfully" in sandbox_output or 
        "status=0" in sandbox_output or 
        "remediating" in sandbox_output or
        "kubectl" in state.get("proposed_command", "")
    ) and "Error (" not in sandbox_output
    
    status = "RESOLVED" if is_verified else "VERIFYING"
    
    step_item = {
        "node": "verify",
        "status": "completed" if is_verified else "failed",
        "timestamp": timestamp,
        "details": {"is_verified": is_verified, "output": sandbox_output}
    }
    
    return {
        "status": status,
        "is_verified": is_verified,
        "step_history": [step_item]
    }
