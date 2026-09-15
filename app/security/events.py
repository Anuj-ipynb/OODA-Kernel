import re
from typing import Any

from app.security.models import SecurityEvent, SeverityLevel


def parse_syslog_line(line: str) -> SecurityEvent:
    """Parses standard syslog and auth log lines into normalized SecurityEvent instances."""
    severity: SeverityLevel = "LOW"
    event_type = "syslog_entry"
    
    line_lower = line.lower()
    if "failed password" in line_lower or "authentication failure" in line_lower:
        event_type = "auth_failure"
        severity = "HIGH"
    elif "sudo" in line_lower or "root" in line_lower:
        event_type = "privilege_access"
        severity = "MEDIUM"
    elif "error" in line_lower or "critical" in line_lower:
        event_type = "system_error"
        severity = "MEDIUM"

    # Extract IP address pattern if present
    ip_match = re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", line)
    src_ip = ip_match.group(0) if ip_match else None

    # Extract user pattern if present
    user_match = re.search(r"for (invalid user )?(\w+)", line)
    user_id = user_match.group(2) if user_match else None

    return SecurityEvent(
        source="syslog",
        event_type=event_type,
        user_id=user_id,
        src_ip=src_ip,
        severity=severity,
        raw_data={"log_line": line}
    )


def normalize_alertmanager_payload(payload: dict[str, Any]) -> list[SecurityEvent]:
    """Normalizes Prometheus Alertmanager JSON webhook payloads."""
    events = []
    alerts = payload.get("alerts", [])
    
    for alert in alerts:
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        alert_name = labels.get("alertname", "PrometheusAlert")
        status = alert.get("status", "firing").upper()
        
        raw_sev = labels.get("severity", "warning").lower()
        severity: SeverityLevel = "HIGH" if raw_sev in ["critical", "high"] else "MEDIUM"

        summary = annotations.get("summary") or annotations.get("description") or alert_name

        events.append(
            SecurityEvent(
                source="prometheus_alertmanager",
                event_type=f"alertmanager_{alert_name.lower()}",
                severity=severity,
                raw_data={"alertname": alert_name, "status": status, "summary": summary, "labels": labels}
            )
        )
    
    if not events:
        events.append(
            SecurityEvent(
                source="prometheus_alertmanager",
                event_type="alertmanager_raw",
                severity="MEDIUM",
                raw_data=payload
            )
        )

    return events


def normalize_pagerduty_payload(payload: dict[str, Any]) -> list[SecurityEvent]:
    """Normalizes PagerDuty incident JSON webhook payloads."""
    events = []
    messages = payload.get("messages", [])
    
    for msg in messages:
        incident = msg.get("incident", {})
        title = incident.get("title", "PagerDuty Incident")
        service = incident.get("service", {}).get("summary", "Unknown Service")
        urgency = incident.get("urgency", "high").lower()
        
        severity: SeverityLevel = "CRITICAL" if urgency == "high" else "MEDIUM"

        events.append(
            SecurityEvent(
                source="pagerduty",
                event_type="pagerduty_incident_trigger",
                severity=severity,
                raw_data={"title": title, "service": service, "urgency": urgency, "incident_id": incident.get("id")}
            )
        )

    if not events:
        events.append(
            SecurityEvent(
                source="pagerduty",
                event_type="pagerduty_raw",
                severity="MEDIUM",
                raw_data=payload
            )
        )

    return events


def normalize_otel_payload(payload: dict[str, Any]) -> list[SecurityEvent]:
    """Normalizes OpenTelemetry log/trace payload dictionaries."""
    events = []
    resource_logs = payload.get("resourceLogs", [])
    
    for rlog in resource_logs:
        for scope in rlog.get("scopeLogs", []):
            for record in scope.get("logRecords", []):
                body = record.get("body", {}).get("stringValue", str(record))
                events.append(
                    SecurityEvent(
                        source="opentelemetry",
                        event_type="otel_log",
                        severity="MEDIUM",
                        raw_data={"log_body": body, "record": record}
                    )
                )

    if not events:
        events.append(
            SecurityEvent(
                source="opentelemetry",
                event_type="otel_raw",
                severity="MEDIUM",
                raw_data=payload
            )
        )

    return events


def create_synthetic_event(
    event_type: str = "process_spawn",
    command: str = "python exploit.py",
    src_ip: str = "192.168.1.100",
    dst_ip: str = "10.0.0.5",
    severity: SeverityLevel = "HIGH"
) -> SecurityEvent:
    """Helper creating synthetic SecurityEvent for tests and cyber range scenarios."""
    return SecurityEvent(
        source="synthetic_cyber_range",
        event_type=event_type,
        host_id="victim-host-01",
        user_id="root",
        process_id=4096,
        process_name="python",
        src_ip=src_ip,
        dst_ip=dst_ip,
        command=command,
        severity=severity,
        raw_data={"synthetic": True}
    )
