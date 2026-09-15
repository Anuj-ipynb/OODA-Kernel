import asyncio
import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from langgraph.types import Command
from pydantic import BaseModel, Field

from app.agents.graph import create_ooda_graph
from app.core.state import IncidentState

logger = logging.getLogger(__name__)

router = APIRouter()
graph = create_ooda_graph()

class IncidentSubmitRequest(BaseModel):
    telemetry: str
    execution_mode: str | None = Field(default="mock", description="mock | staging | production")
    max_retries: int | None = 3

class ApprovalRequest(BaseModel):
    approved: bool = True
    operator_id: str | None = Field(default="OPERATOR_ADMIN", description="ID of human operator approving action")
    override_command: str | None = None
    operator_notes: str | None = None

@router.post("/submit")
async def submit_incident(req: IncidentSubmitRequest):
    """
    Ingests raw incident telemetry and starts state graph processing.
    """
    incident_id = str(uuid.uuid4())
    execution_mode = req.execution_mode if req.execution_mode in ["mock", "staging", "production"] else "mock"
    
    initial_state = IncidentState(
        incident_id=incident_id,
        status="SUBMITTED",
        execution_mode=execution_mode,
        telemetry_logs=req.telemetry,
        root_cause_analysis="",
        proposed_command="",
        rollback_command="",
        risk_score=0.0,
        is_destructive=False,
        sandbox_output=None,
        is_verified=False,
        retry_count=0,
        max_retries=req.max_retries or 3,
        step_history=[],
        audit_trail=[],
        error_log=[]
    )
    
    config = {"configurable": {"thread_id": incident_id}}
    
    result = await asyncio.to_thread(graph.invoke, initial_state, config=config)
    state_snapshot = graph.get_state(config)
    is_interrupted = len(state_snapshot.tasks) > 0 and any(task.interrupts for task in state_snapshot.tasks)
    status = "AWAITING_APPROVAL" if is_interrupted else result.get("status", "COMPLETED")
    
    return {
        "incident_id": incident_id,
        "status": status,
        "execution_mode": execution_mode,
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
        "operator_id": req.operator_id or "OPERATOR_ADMIN",
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

# --- Live Webhook Ingestion Routes ---

@router.post("/webhook/alertmanager")
async def webhook_alertmanager(payload: dict[str, Any], mode: str | None = "mock"):
    """Ingest webhook telemetry stream from Prometheus Alertmanager."""
    alerts = payload.get("alerts", [])
    telemetry_parts = []
    for alert in alerts:
        annotations = alert.get("annotations", {})
        summary = annotations.get("summary") or annotations.get("description") or alert.get("labels", {}).get("alertname", "Alert")
        telemetry_parts.append(f"[PROMETHEUS ALERT] {alert.get('status', 'FIRING').upper()}: {summary}")
        
    telemetry_logs = "\n".join(telemetry_parts) if telemetry_parts else f"[PROMETHEUS ALERT] {json.dumps(payload)}"
    return await submit_incident(IncidentSubmitRequest(telemetry=telemetry_logs, execution_mode=mode))

@router.post("/webhook/pagerduty")
async def webhook_pagerduty(payload: dict[str, Any], mode: str | None = "mock"):
    """Ingest webhook telemetry stream from PagerDuty."""
    messages = payload.get("messages", [])
    telemetry_parts = []
    for msg in messages:
        incident = msg.get("incident", {})
        title = incident.get("title", "PagerDuty Triggered Incident")
        service = incident.get("service", {}).get("summary", "Unknown Service")
        telemetry_parts.append(f"[PAGERDUTY ALERT] Service: {service} | Details: {title}")
        
    telemetry_logs = "\n".join(telemetry_parts) if telemetry_parts else f"[PAGERDUTY ALERT] {json.dumps(payload)}"
    return await submit_incident(IncidentSubmitRequest(telemetry=telemetry_logs, execution_mode=mode))

@router.post("/webhook/otel")
async def webhook_otel(payload: dict[str, Any], mode: str | None = "mock"):
    """Ingest telemetry stream from OpenTelemetry log formatters."""
    resource_logs = payload.get("resourceLogs", [])
    telemetry_parts = []
    for rlog in resource_logs:
        for scope in rlog.get("scopeLogs", []):
            for record in scope.get("logRecords", []):
                body = record.get("body", {}).get("stringValue", str(record))
                telemetry_parts.append(f"[OPENTELEMETRY LOG] {body}")
                
    telemetry_logs = "\n".join(telemetry_parts) if telemetry_parts else f"[OPENTELEMETRY TRACE] {json.dumps(payload)}"
    return await submit_incident(IncidentSubmitRequest(telemetry=telemetry_logs, execution_mode=mode))

# --- Live WebSocket Telemetry Stream Endpoint ---

@router.websocket("/ws/telemetry")
async def websocket_telemetry_stream(websocket: WebSocket):
    """
    WebSocket Endpoint: Ingests real-time telemetry packets and streams live OODA state updates back to clients.
    """
    await websocket.accept()
    logger.info("WebSocket telemetry stream connected.")
    try:
        while True:
            data_str = await websocket.receive_text()
            try:
                packet = json.loads(data_str)
                telemetry_text = packet.get("telemetry", data_str)
                mode = packet.get("execution_mode", "mock")
            except Exception:  # noqa: BLE001
                telemetry_text = data_str
                mode = "mock"

            submit_req = IncidentSubmitRequest(telemetry=telemetry_text, execution_mode=mode)
            res = await submit_incident(submit_req)
            await websocket.send_text(json.dumps(res))
    except WebSocketDisconnect:
        logger.info("WebSocket telemetry stream disconnected.")
    except Exception as e:  # noqa: BLE001
        logger.error(f"WebSocket error: {e}")
