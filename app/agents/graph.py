import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import interrupt

from app.core.state import IncidentState
from app.agents.observe import observe_node
from app.agents.orient import orient_node
from app.agents.decide import decide_node
from app.agents.act import act_node
from app.agents.verify import verify_node
from app.agents.rollback import rollback_node

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "ooda_checkpoint.db")

def get_sqlite_checkpointer():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    saver = SqliteSaver(conn)
    saver.setup()
    return saver

def hitl_gateway_node(state: IncidentState) -> dict:
    """
    HITL Gateway Node: Invokes interrupt if risk_score > 0.70, action is destructive,
    or execution environment is set to 'production'.
    """
    risk_score = state.get("risk_score", 0.0)
    is_destructive = state.get("is_destructive", False)
    mode = state.get("execution_mode", "mock")
    
    requires_approval = (risk_score > 0.70) or is_destructive or (mode == "production")
    
    if requires_approval:
        approval = interrupt({
            "incident_id": state.get("incident_id"),
            "proposed_command": state.get("proposed_command"),
            "rollback_command": state.get("rollback_command"),
            "risk_score": risk_score,
            "is_destructive": is_destructive,
            "execution_mode": mode,
            "reason": f"Action halts: risk_score ({risk_score:.2f}) > 0.70, destructive ({is_destructive}), or environment is '{mode}'."
        })
        
        timestamp = datetime.now(timezone.utc).isoformat()
        operator_id = "UNKNOWN_OPERATOR"
        if isinstance(approval, dict):
            operator_id = approval.get("operator_id", "OPERATOR")
            if not approval.get("approved", True):
                audit_reject = {
                    "event_id": str(uuid.uuid4()),
                    "timestamp": timestamp,
                    "operator_id": operator_id,
                    "action": "HITL_REJECTED",
                    "status": "ABORTED",
                    "details": {
                        "proposed_command": state.get("proposed_command"),
                        "operator_notes": approval.get("operator_notes", "Operator rejected execution")
                    }
                }
                return {
                    "status": "FAILED",
                    "audit_trail": [audit_reject],
                    "error_log": [f"[HITL REJECTED] Operator ({operator_id}) rejected command."]
                }
        
        audit_approve = {
            "event_id": str(uuid.uuid4()),
            "timestamp": timestamp,
            "operator_id": operator_id,
            "action": "HITL_APPROVED",
            "status": "CONFIRMED",
            "details": {
                "proposed_command": state.get("proposed_command"),
                "risk_score": risk_score,
                "execution_mode": mode
            }
        }
        return {
            "status": "AWAITING_APPROVAL_PASSED",
            "audit_trail": [audit_approve]
        }
            
    return {"status": "AWAITING_APPROVAL_PASSED"}

def route_after_hitl(state: IncidentState) -> str:
    if state.get("status") == "FAILED":
        return END
    return "act"

def route_after_verify(state: IncidentState) -> str:
    if state.get("is_verified", False):
        return END
        
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    
    if retry_count < max_retries:
        return "rollback"
    return END

def create_ooda_graph(checkpointer=None):
    """
    Compiles the stateful OODA StateGraph with checkpointer and HITL gateway.
    """
    if checkpointer is None:
        checkpointer = get_sqlite_checkpointer()
        
    workflow = StateGraph(IncidentState)

    # Register Nodes
    workflow.add_node("observe", observe_node)
    workflow.add_node("orient", orient_node)
    workflow.add_node("decide", decide_node)
    workflow.add_node("hitl_gateway", hitl_gateway_node)
    workflow.add_node("act", act_node)
    workflow.add_node("verify", verify_node)
    workflow.add_node("rollback", rollback_node)

    # Define Graph Edges
    workflow.set_entry_point("observe")
    workflow.add_edge("observe", "orient")
    workflow.add_edge("orient", "decide")
    workflow.add_edge("decide", "hitl_gateway")
    
    # Conditional edge after HITL approval with explicit path mapping
    workflow.add_conditional_edges(
        "hitl_gateway",
        route_after_hitl,
        {"act": "act", END: END}
    )
    
    workflow.add_edge("act", "verify")
    
    # Conditional edge after Verification with explicit path mapping
    workflow.add_conditional_edges(
        "verify",
        route_after_verify,
        {END: END, "rollback": "rollback"}
    )
    workflow.add_edge("rollback", "orient")

    return workflow.compile(checkpointer=checkpointer)
