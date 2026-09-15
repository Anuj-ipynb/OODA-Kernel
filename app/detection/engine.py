import logging

from app.detection.anomaly import AnomalyDetector
from app.detection.rules import (
    BruteForceAuthRule,
    NetworkEgressAnomalyRule,
    SuspiciousProcessRule,
)
from app.security.models import DetectionAlert, SecurityEvent

logger = logging.getLogger(__name__)


class DetectionEngine:
    """
    Detection Engine orchestrating deterministic security rules and statistical anomaly detectors.
    Ensures security alerts do NOT rely purely on LLM output.
    """
    def __init__(self) -> None:
        self.rules = [
            BruteForceAuthRule(threshold=3),
            SuspiciousProcessRule(),
            NetworkEgressAnomalyRule(),
        ]
        self.anomaly_detector = AnomalyDetector(z_threshold=2.5)

    def process_events(self, events: list[SecurityEvent]) -> list[DetectionAlert]:
        alerts: list[DetectionAlert] = []

        # 1. Evaluate deterministic rules
        for rule in self.rules:
            try:
                rule_alerts = rule.evaluate(events)
                alerts.extend(rule_alerts)
            except Exception as e:  # noqa: BLE001
                logger.error(f"[DETECTION ENGINE] Rule '{rule.name}' evaluation error: {e}")

        # 2. Evaluate statistical anomaly detector
        try:
            anom_alerts = self.anomaly_detector.detect_command_length_anomalies(events)
            alerts.extend(anom_alerts)
        except Exception as e:  # noqa: BLE001
            logger.error(f"[DETECTION ENGINE] Anomaly detector error: {e}")

        logger.info(f"[DETECTION ENGINE] Processed {len(events)} events -> Generated {len(alerts)} alerts.")
        return alerts
