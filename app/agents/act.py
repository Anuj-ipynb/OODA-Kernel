from datetime import datetime, timezone
from app.core.state import IncidentState
from app.sandbox.docker_exec import docker_exec

def act_node(state: IncidentState) -> dict:
    """
    Act Node: Executes the proposed remediation command inside the isolated sandbox environment.
    """
    command = state.get("proposed_command", "echo 'no command specified'")
    timestamp = datetime.now(timezone.utc).isoformat()
    
    output = docker_exec(command)
    
    step_item = {
        "node": "act",
        "status": "completed",
        "timestamp": timestamp,
        "details": {"command": command, "output": output}
    }
    
    return {
        "status": "ACTING",
        "sandbox_output": output,
        "step_history": [step_item]
    }
