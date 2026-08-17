from typing import List, Optional
from pydantic import BaseModel, Field

class OrientAnalysisSchema(BaseModel):
    root_cause: str = Field(description="Summary of the topological or root cause of the incident")
    impacted_services: List[str] = Field(default_factory=list, description="List of microservices or system components affected")
    confidence_score: float = Field(default=0.9, description="Confidence score between 0.0 and 1.0")
    reasoning: Optional[str] = Field(default="", description="Chain-of-thought analysis or reasoning behind the diagnosis")

class DecideSchema(BaseModel):
    proposed_command: str = Field(description="Exact executable shell or python command for sandbox execution")
    risk_score: float = Field(description="Risk assessment score between 0.0 (safe) and 1.0 (extremely risky/destructive)")
    is_destructive: bool = Field(default=False, description="True if the proposed action drops data, deletes files, or restarts critical services")
    explanation: str = Field(description="Explanation for why this remediation command was selected")
