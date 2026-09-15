import logging

from pydantic import BaseModel

from app.security.models import DetectionAlert, Evidence, SecurityEvent

logger = logging.getLogger(__name__)


class TimelineEntry(BaseModel):
    """Chronological event representation for SOC attack timelines."""
    step_index: int
    timestamp: str
    source: str
    event_type: str
    severity: str
    summary: str
    actor: str | None = None
    target: str | None = None
    event_id: str


class EvidenceStore:
    """
    Immutable Evidence Store indexing SecurityEvents, Evidence units, and DetectionAlerts
    grounding threat hypotheses without data loss.
    """
    def __init__(self) -> None:
        self.events: dict[str, SecurityEvent] = {}
        self.evidence: dict[str, Evidence] = {}
        self.alerts: dict[str, DetectionAlert] = {}
        
        # Secondary indexes for fast lookup
        self.by_host: dict[str, list[str]] = {}
        self.by_user: dict[str, list[str]] = {}
        self.by_ip: dict[str, list[str]] = {}

    def add_event(self, event: SecurityEvent) -> None:
        self.events[event.event_id] = event
        
        if event.host_id:
            self.by_host.setdefault(event.host_id, []).append(event.event_id)
        if event.user_id:
            self.by_user.setdefault(event.user_id, []).append(event.event_id)
        if event.src_ip:
            self.by_ip.setdefault(event.src_ip, []).append(event.event_id)
        if event.dst_ip:
            self.by_ip.setdefault(event.dst_ip, []).append(event.event_id)

    def add_evidence(self, ev: Evidence) -> None:
        self.evidence[ev.evidence_id] = ev

    def add_alert(self, alert: DetectionAlert) -> None:
        self.alerts[alert.alert_id] = alert
        for ev in alert.evidence:
            self.add_evidence(ev)
        for evt in alert.events:
            self.add_event(evt)

    def get_events_for_host(self, host_id: str) -> list[SecurityEvent]:
        event_ids = self.by_host.get(host_id, [])
        return [self.events[eid] for eid in event_ids if eid in self.events]

    def get_events_for_user(self, user_id: str) -> list[SecurityEvent]:
        event_ids = self.by_user.get(user_id, [])
        return [self.events[eid] for eid in event_ids if eid in self.events]

    def get_events_for_ip(self, ip: str) -> list[SecurityEvent]:
        event_ids = self.by_ip.get(ip, [])
        return [self.events[eid] for eid in event_ids if eid in self.events]


class TimelineBuilder:
    """Generates ordered chronological attack timelines from evidence and events."""
    @staticmethod
    def build_timeline(events: list[SecurityEvent]) -> list[TimelineEntry]:
        sorted_events = sorted(events, key=lambda e: e.timestamp)
        timeline: list[TimelineEntry] = []

        for idx, evt in enumerate(sorted_events, start=1):
            cmd_str = f"Executed '{evt.command}'" if evt.command else evt.event_type
            summary = f"[{evt.source.upper()}] {cmd_str}"
            actor = evt.user_id or evt.src_ip
            target = evt.host_id or evt.dst_ip

            timeline.append(
                TimelineEntry(
                    step_index=idx,
                    timestamp=evt.timestamp.isoformat(),
                    source=evt.source,
                    event_type=evt.event_type,
                    severity=evt.severity,
                    summary=summary,
                    actor=actor,
                    target=target,
                    event_id=evt.event_id
                )
            )

        return timeline
