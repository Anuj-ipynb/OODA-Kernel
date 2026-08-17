import uuid
import asyncio
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from langgraph.types import Command

from app.agents.graph import create_ooda_graph
from app.core.state import IncidentState

router = APIRouter()
graph = create_ooda_graph()

class IncidentSubmitRequest(BaseModel):
    telemetry: str
    max_retries: Optional[int] = 3

class ApprovalRequest(BaseModel):
    approved: bool = True
    override_command: Optional[str] = None
    operator_notes: Optional[str] = None

@router.post("/submit")
async def submit_incident(req: IncidentSubmitRequest):
    """
    Ingests raw incident telemetry and starts asynchronous state graph processing.
    """
    incident_id = str(uuid.uuid4())
    initial_state = IncidentState(
        incident_id=incident_id,
        status="SUBMITTED",
        telemetry_logs=req.telemetry,
        root_cause_analysis="",
        proposed_command="",
        risk_score=0.0,
        is_destructive=False,
        sandbox_output=None,
        is_verified=False,
        retry_count=0,
        max_retries=req.max_retries,
        step_history=[],
        error_log=[]
    )
    
    config = {"configurable": {"thread_id": incident_id}}
    
    # Run graph execution in a thread pool to prevent blocking the event loop
    result = await asyncio.to_thread(graph.invoke, initial_state, config=config)
    
    # Check if graph interrupted at HITL gateway
    state_snapshot = graph.get_state(config)
    is_interrupted = len(state_snapshot.tasks) > 0 and any(task.interrupts for task in state_snapshot.tasks)
    
    status = "AWAITING_APPROVAL" if is_interrupted else result.get("status", "COMPLETED")
    
    return {
        "incident_id": incident_id,
        "status": status,
        "is_interrupted": is_interrupted,
        "state": result
    }

@router.post("/{incident_id}/approve")
async def approve_incident(incident_id: str, req: ApprovalRequest):
    """
    Resumes graph execution for an interrupted incident requiring operator sign-off.
    """
    config = {"configurable": {"thread_id": incident_id}}
    state_snapshot = graph.get_state(config)
    
    if not state_snapshot.values:
        raise HTTPException(status_code=404, detail="Incident not found or no active thread.")
        
    resume_payload = {
        "approved": req.approved,
        "override_command": req.override_command,
        "operator_notes": req.operator_notes
    }
    
    result = await asyncio.to_thread(
        graph.invoke, Command(resume=resume_payload), config=config
    )
    
    return {
        "incident_id": incident_id,
        "status": result.get("status", "RESOLVED"),
        "is_verified": result.get("is_verified", False),
        "result": result
    }

@router.get("/{incident_id}/state")
async def get_incident_state(incident_id: str):
    """
    Retrieves the current state snapshot and execution history for an incident.
    """
    config = {"configurable": {"thread_id": incident_id}}
    state_snapshot = graph.get_state(config)
    
    if not state_snapshot.values:
        raise HTTPException(status_code=404, detail="Incident state not found.")
        
    return {
        "incident_id": incident_id,
        "values": state_snapshot.values,
        "next": state_snapshot.next
    }
