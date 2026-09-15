from fastapi import FastAPI, WebSocket

from app.api.endpoints import router as incident_router
from app.api.endpoints import websocket_telemetry_stream

app = FastAPI(
    title="OODA-Kernel API",
    description="Autonomous Incident Remediation Engine with Human-in-the-Loop Guardrails",
    version="0.3.0"
)

app.include_router(incident_router, prefix="/api/incident", tags=["Incidents"])

@app.websocket("/ws/telemetry")
async def websocket_root_proxy(websocket: WebSocket):
    await websocket_telemetry_stream(websocket)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "engine": "OODA-Kernel", "version": "0.3.0"}
