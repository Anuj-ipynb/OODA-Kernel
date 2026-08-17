from typing import TypedDict, List, Dict, Any, Optional, Annotated
import operator

class StepHistoryItem(TypedDict):
    node: str
    status: str  # "PENDING", "RUNNING", "PAUSED_HITL", "RESOLVED", "FAILED", "COMPLETED"
    timestamp: str
    latency_ms: Optional[float]
    details: Optional[Dict[str, Any]]

class IncidentState(TypedDict):
    # Incident Identification
    incident_id: str
    status: str  # "OBSERVING", "ORIENTING", "DECIDING", "AWAITING_APPROVAL", "ACTING", "VERIFYING", "RESOLVED", "FAILED", "ROLLING_BACK"
    execution_mode: str  # "mock", "staging", "production"
    
    # Telemetry & Analysis
    telemetry_logs: str
    root_cause_analysis: Any
    
    # Action Formulation & Risk Assessment
    proposed_command: str
    rollback_command: Optional[str]
    risk_score: float  # Range: 0.0 to 1.0
    is_destructive: bool
    
    # Sandbox Execution & Verification
    sandbox_output: Optional[str]
    is_verified: bool
    
    # Loop Control & History (Reducers for safe state accumulation)
    retry_count: int
    max_retries: int
    step_history: Annotated[List[StepHistoryItem], operator.add]
    audit_trail: Annotated[List[Dict[str, Any]], operator.add]
    error_log: Annotated[List[str], operator.add]
