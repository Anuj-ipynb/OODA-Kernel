import time
import uuid
from datetime import datetime, timezone
from app.core.state import IncidentState
from app.sandbox.docker_exec import docker_exec

def rollback_node(state: IncidentState) -> dict:
    """
    Rollback Node: Automatically executes the rollback command when verification fails,
    records immutable audit traces, and prepares state for re-orientation.
    """
    start_time = time.time()
    current_retries = state.get("retry_count", 0)
    timestamp = datetime.now(timezone.utc).isoformat()
    new_retries = current_retries + 1
    
    rollback_cmd = state.get("rollback_command") or f"echo 'ROLLBACK FALLBACK FOR: {state.get('proposed_command')}'"
    mode = state.get("execution_mode", "mock")
    
    # Automatically execute rollback command
    rollback_output = docker_exec(rollback_cmd, execution_mode=mode)
    latency_ms = round((time.time() - start_time) * 1000, 2)
    
    error_msg = f"[ROLLBACK EXECUTED] Verification failed (Attempt {new_retries}/{state.get('max_retries', 3)}). Executed: {rollback_cmd}"
    
    step_item = {
        "node": "rollback",
        "status": "FAILED",
        "timestamp": timestamp,
        "latency_ms": latency_ms,
        "details": {
            "retry_count": new_retries,
            "rollback_command": rollback_cmd,
            "rollback_output": rollback_output,
            "reason": error_msg
        }
    }
    
    # Immutable audit record
    audit_event = {
        "event_id": str(uuid.uuid4()),
        "timestamp": timestamp,
        "operator_id": state.get("operator_id", "SYSTEM_AUTO_ROLLBACK"),
        "action": "AUTOMATED_ROLLBACK_EXECUTION",
        "status": "COMPLETED",
        "details": {
            "retry_attempt": new_retries,
            "proposed_command": state.get("proposed_command"),
            "rollback_command": rollback_cmd,
            "rollback_output": rollback_output,
            "execution_mode": mode,
            "state_snapshot_status": state.get("status")
        }
    }
    
    return {
        "status": "ROLLING_BACK",
        "retry_count": new_retries,
        "is_verified": False,
        "error_log": [error_msg],
        "step_history": [step_item],
        "audit_trail": [audit_event]
    }
