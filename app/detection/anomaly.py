import math

from app.security.models import DetectionAlert, Evidence, SecurityEvent


class AnomalyDetector:
    """
    Statistical Anomaly Detector using Z-Score & Frequency Analysis
    Detects abnormal command length bursts and event rate spikes.
    """
    def __init__(self, z_threshold: float = 3.0) -> None:
        self.z_threshold = z_threshold

    def detect_command_length_anomalies(self, events: list[SecurityEvent]) -> list[DetectionAlert]:
        alerts = []
        cmd_lengths = []
        valid_events = []

        for evt in events:
            if evt.command:
                cmd_lengths.append(len(evt.command))
                valid_events.append(evt)

        if len(cmd_lengths) < 3:
            return alerts

        mean = sum(cmd_lengths) / len(cmd_lengths)
        variance = sum((x - mean) ** 2 for x in cmd_lengths) / len(cmd_lengths)
        std_dev = math.sqrt(variance)

        if std_dev == 0:
            return alerts

        for evt, length in zip(valid_events, cmd_lengths, strict=False):
            z_score = (length - mean) / std_dev
            if z_score > self.z_threshold:
                ev = Evidence(
                    event_id=evt.event_id,
                    observation=f"Anomalous command length ({length} chars, z-score={z_score:.2f})",
                    source=evt.source,
                    timestamp=evt.timestamp,
                    confidence=min(0.5 + (z_score * 0.1), 0.95)
                )
                alerts.append(
                    DetectionAlert(
                        title=f"Statistical Anomaly: Abnormal Command Length (z-score: {z_score:.2f})",
                        rule_id="ANOM-001",
                        severity="MEDIUM",
                        events=[evt],
                        evidence=[ev]
                    )
                )

        return alerts
