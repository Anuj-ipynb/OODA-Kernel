from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt

from app.core.state import IncidentState
from app.agents.observe import observe_node
from app.agents.orient import orient_node
from app.agents.decide import decide_node
from app.agents.act import act_node
from app.agents.verify import verify_node
from app.agents.rollback import rollback_node

def hitl_gateway_node(state: IncidentState) -> dict:
    """
    HITL Gateway Node: Invokes interrupt if risk_score > 0.70 or action is destructive.
    """
    risk_score = state.get("risk_score", 0.0)
    is_destructive = state.get("is_destructive", False)
    
    if risk_score > 0.70 or is_destructive:
        # Pause execution and stream payload to human approval dashboard
        approval = interrupt({
            "incident_id": state.get("incident_id"),
            "proposed_command": state.get("proposed_command"),
            "risk_score": risk_score,
            "is_destructive": is_destructive,
            "reason": "Action exceeds risk threshold (0.70) or is marked as destructive."
        })
        
        # When resumed via Command(resume={"approved": True/False, ...})
        if isinstance(approval, dict) and not approval.get("approved", True):
            return {
                "status": "FAILED",
                "error_log": ["[HITL REJECTED] Operator rejected proposed remediation command."]
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
        checkpointer = MemorySaver()
        
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
