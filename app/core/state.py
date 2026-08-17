from typing import TypedDict, List, Dict, Any, Optional, Annotated
import operator

class StepHistoryItem(TypedDict):
    node: str
    status: str
    timestamp: str
    details: Optional[Dict[str, Any]]

class IncidentState(TypedDict):
    # Incident Identification
    incident_id: str
    status: str  # "OBSERVING", "ORIENTING", "DECIDING", "AWAITING_APPROVAL", "ACTING", "VERIFYING", "RESOLVED", "FAILED"
    
    # Telemetry & Analysis
    telemetry_logs: str
    root_cause_analysis: str
    
    # Action Formulation & Risk Assessment
    proposed_command: str
    risk_score: float  # Range: 0.0 to 1.0
    is_destructive: bool
    
    # Sandbox Execution & Verification
    sandbox_output: Optional[str]
    is_verified: bool
    
    # Loop Control & History (Reducers for safe state accumulation)
    retry_count: int
    max_retries: int
    step_history: Annotated[List[StepHistoryItem], operator.add]
    error_log: Annotated[List[str], operator.add]
