import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

SeverityLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
IndicatorType = Literal["IP", "DOMAIN", "URL", "HASH", "USER", "PROCESS", "FILE"]

class SecurityEvent(BaseModel):
    """Normalized security event representation preserving normalized fields + raw evidence."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source: str = Field(..., description="Telemetry source identifier (e.g. syslog, otel, alertmanager)")
    event_type: str = Field(..., description="Normalized event classification (e.g. auth_failure, process_spawn)")

    host_id: str | None = None
    user_id: str | None = None
    process_id: int | None = None
    process_name: str | None = None

    src_ip: str | None = None
    dst_ip: str | None = None
    src_port: int | None = None
    dst_port: int | None = None

    command: str | None = None
    file_path: str | None = None

    severity: SeverityLevel = "MEDIUM"
    raw_data: dict[str, Any] = Field(default_factory=dict)


class Indicator(BaseModel):
    """Threat indicator artifact (IOC)."""
    indicator_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    indicator_type: IndicatorType
    value: str
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    severity: SeverityLevel = "MEDIUM"
    description: str | None = None


class Evidence(BaseModel):
    """Immutable evidence unit grounding investigation conclusions."""
    evidence_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_id: str
    observation: str
    source: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)


class DetectionAlert(BaseModel):
    """Correlated security alert output by detection engine."""
    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    rule_id: str
    severity: SeverityLevel = "HIGH"
    events: list[SecurityEvent] = Field(default_factory=list)
    indicators: list[Indicator] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
