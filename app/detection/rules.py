import re
from typing import Protocol

from app.security.models import DetectionAlert, Evidence, Indicator, SecurityEvent

SUSPICIOUS_CMD_PATTERNS = [
    r"nc\s+.*-e",
    r"bash\s+-i",
    r"curl\s+.*\|\s*sh",
    r"wget\s+.*\|\s*sh",
    r"/tmp/[a-zA-Z0-9_-]+",
    r"mimikatz",
    r"nmap",
    r"chmod\s+777",
    r"shadow",
]

SUSPICIOUS_PORTS = {4444, 6667, 1337, 31337, 8888}


class DetectionRule(Protocol):
    rule_id: str
    name: str

    def evaluate(self, events: list[SecurityEvent]) -> list[DetectionAlert]:
        ...


class BruteForceAuthRule:
    rule_id = "RULE-001"
    name = "Brute Force Authentication Attempt"

    def __init__(self, threshold: int = 3) -> None:
        self.threshold = threshold

    def evaluate(self, events: list[SecurityEvent]) -> list[DetectionAlert]:
        alerts = []
        ip_counts: dict[str, list[SecurityEvent]] = {}

        for evt in events:
            if evt.event_type == "auth_failure" and evt.src_ip:
                ip_counts.setdefault(evt.src_ip, []).append(evt)

        for ip, evt_list in ip_counts.items():
            if len(evt_list) >= self.threshold:
                evidences = [
                    Evidence(
                        event_id=e.event_id,
                        observation=f"Authentication failure from IP {ip} (User: {e.user_id or 'unknown'})",
                        source=e.source,
                        timestamp=e.timestamp,
                        confidence=0.95
                    )
                    for e in evt_list
                ]
                indicators = [
                    Indicator(indicator_type="IP", value=ip, confidence=0.9, severity="HIGH", description="Brute force source IP")
                ]
                alerts.append(
                    DetectionAlert(
                        title=f"Brute Force Auth Attack from {ip} ({len(evt_list)} attempts)",
                        rule_id=self.rule_id,
                        severity="HIGH",
                        events=evt_list,
                        indicators=indicators,
                        evidence=evidences
                    )
                )
        return alerts


class SuspiciousProcessRule:
    rule_id = "RULE-002"
    name = "Suspicious Process / Shell Command Execution"

    def evaluate(self, events: list[SecurityEvent]) -> list[DetectionAlert]:
        alerts = []
        for evt in events:
            cmd = evt.command or (evt.raw_data.get("log_line") if isinstance(evt.raw_data, dict) else None)
            if not cmd:
                continue

            for pattern in SUSPICIOUS_CMD_PATTERNS:
                if re.search(pattern, cmd, re.IGNORECASE):
                    ev = Evidence(
                        event_id=evt.event_id,
                        observation=f"Suspicious command matching pattern '{pattern}': {cmd}",
                        source=evt.source,
                        timestamp=evt.timestamp,
                        confidence=0.90
                    )
                    indicators = []
                    if evt.src_ip:
                        indicators.append(Indicator(indicator_type="IP", value=evt.src_ip, confidence=0.8, severity="HIGH"))
                    if evt.process_name:
                        indicators.append(Indicator(indicator_type="PROCESS", value=evt.process_name, confidence=0.8, severity="HIGH"))

                    alerts.append(
                        DetectionAlert(
                            title=f"Suspicious Execution Detected: {pattern}",
                            rule_id=self.rule_id,
                            severity="HIGH",
                            events=[evt],
                            indicators=indicators,
                            evidence=[ev]
                        )
                    )
                    break
        return alerts


class NetworkEgressAnomalyRule:
    rule_id = "RULE-003"
    name = "Suspicious Network Egress Connection"

    def evaluate(self, events: list[SecurityEvent]) -> list[DetectionAlert]:
        alerts = []
        for evt in events:
            if evt.dst_port and evt.dst_port in SUSPICIOUS_PORTS:
                ev = Evidence(
                    event_id=evt.event_id,
                    observation=f"Connection to high-risk port {evt.dst_port} at {evt.dst_ip or 'unknown'}",
                    source=evt.source,
                    timestamp=evt.timestamp,
                    confidence=0.85
                )
                indicators = []
                if evt.dst_ip:
                    indicators.append(Indicator(indicator_type="IP", value=evt.dst_ip, confidence=0.85, severity="HIGH", description="C2 / Egress Destination IP"))

                alerts.append(
                    DetectionAlert(
                        title=f"High-Risk Network Egress Port {evt.dst_port}",
                        rule_id=self.rule_id,
                        severity="HIGH",
                        events=[evt],
                        indicators=indicators,
                        evidence=[ev]
                    )
                )
        return alerts
