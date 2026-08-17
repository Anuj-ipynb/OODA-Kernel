from fastapi import FastAPI
from app.api.endpoints import router as incident_router

app = FastAPI(
    title="OODA-Kernel API",
    description="Autonomous Incident Remediation Engine with Human-in-the-Loop Guardrails",
    version="0.2.0"
)

app.include_router(incident_router, prefix="/api/incident", tags=["Incidents"])

@app.get("/health")
async def health_check():
    return {"status": "healthy", "engine": "OODA-Kernel"}
