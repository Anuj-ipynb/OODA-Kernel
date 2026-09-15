import time
from datetime import UTC, datetime

from app.core.state import IncidentState
from app.sandbox.docker_exec import docker_exec


def act_node(state: IncidentState) -> dict:
    """
    Act Node: Executes the proposed remediation command inside the targeted execution environment (mock/staging/production).
    """
    start_time = time.time()
    command = state.get("proposed_command", "echo 'no command specified'")
    mode = state.get("execution_mode", "mock")
    timestamp = datetime.now(UTC).isoformat()
    
    output = docker_exec(command, execution_mode=mode)
    latency_ms = round((time.time() - start_time) * 1000, 2)
    
    step_item = {
        "node": "act",
        "status": "COMPLETED",
        "timestamp": timestamp,
        "latency_ms": latency_ms,
        "details": {"command": command, "output": output, "execution_mode": mode}
    }
    
    return {
        "status": "ACTING",
        "sandbox_output": output,
        "step_history": [step_item]
    }
